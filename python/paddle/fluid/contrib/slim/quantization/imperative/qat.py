#   Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import numpy as np
import sys
import paddle
from paddle.fluid import dygraph
from paddle.fluid.dygraph.nn import Conv2D
from paddle.fluid.dygraph.nn import Linear
from paddle.fluid.log_helper import get_logger
from . import quant_nn

__all__ = ['ImperativeQuantAware']

_logger = get_logger(
    __name__, logging.INFO, fmt='%(asctime)s-%(levelname)s: %(message)s')


class ImperativeQuantAware(object):
    """
    Add the fake quant logic for given quantizable layers, namely add the quant_dequant
    computational logic both for activation inputs and weight inputs.
    """

    def __init__(self,
                 weight_bits=8,
                 activation_bits=8,
                 weight_quantize_type='abs_max',
                 activation_quantize_type='moving_average_abs_max',
                 moving_rate=0.9,
                 quantizable_layer_type=['Conv2D', 'Linear']):
        """
        The constructor for ImperativeQuantAware.

        Args:
            weight_bits(int): quantization bit number for weights,
                whereas the bias is not quantized.
            activation_bits(int): quantization bit number for activations.
            weight_quantize_type(str): quantization type for weights,
                which supports 'abs_max' now. The 'moving_average_abs_max'
                usually is not used for weights, since weights are fixed once the
                model is well trained.
            activation_quantize_type(str): quantization type for activations,
                which supports 'abs_max' and 'moving_average_abs_max' now.
                If using 'abs_max' mode, the quantization scale will be calculated
                dynamically each step in both training and testing period. If using
                'moving_average_abs_max', the static quantization scale will be calculated
                during training and used in inference.
            moving_rate(float): the parameter for 'moving_average_abs_max' quantization.
            quantizable_op_type(list[str]): List the type of layers that will be quantized. 
                Default is ['Conv2D', 'Linear']. The quantizable_op_type in
                QuantizationFreezePass and ConvertToInt8Pass must be the same as this.


        Examples:
        .. code-block:: python

            import paddle
            from paddle.fluid.contrib.slim.quantization \
                import ImperativeQuantAware
            from paddle.vision.models \
                import resnet
            
            model = resnet.resnet50(pretrained=True)

            imperative_qat = ImperativeQuantAware(
                weight_quantize_type='abs_max',
                activation_quantize_type='moving_average_abs_max')
            
            # Add the fake quant logical.
            # The original model will be rewrite.
            imperative_qat.quantize(model)

            # Fine-tune the quantized model
            # ...
            
            # Save quant model for the inference.
            paddle.jit.save(
                layer=model,
                model_path="./resnet50_qat",
                input_spec=[
                    paddle.static.InputSpec(
                    shape=[None, 3, 224, 224], dtype='float32')])
        """
        super(ImperativeQuantAware, self).__init__()
        self._weight_bits = weight_bits
        self._activation_bits = activation_bits
        self._moving_rate = moving_rate

        quant_type = {
            'abs_max', 'moving_average_abs_max', 'channel_wise_abs_max'
        }

        assert activation_quantize_type != 'channel_wise_abs_max', \
            "The activation quantization type does not support 'channel_wise_abs_max'."
        if activation_quantize_type not in quant_type:
            raise ValueError(
                "Unknown activation_quantize_type : '%s'. It can only be "
                "'abs_max' or 'moving_average_abs_max' now." %
                (str(activation_quantize_type)))
        if weight_quantize_type not in quant_type:
            raise ValueError(
                "Unknown weight_quantize_type: '%s'. It can only be "
                "'abs_max' or 'moving_average_abs_max' or 'channel_wise_abs_max' now."
                % (str(weight_quantize_type)))
        self._activation_quantize_type = activation_quantize_type
        self._weight_quantize_type = weight_quantize_type

        self._quant_layers_map = {'Conv2D': Conv2D, 'Linear': Linear}
        self._quantizable_layer_type = tuple(
            self._quant_layers_map[layer]
            if layer in self._quant_layers_map else layer
            for layer in quantizable_layer_type)
        for layer in self._quantizable_layer_type:
            assert not isinstance(
                layer, str), "{} is unspported to be quantized.".format(layer)

    def quantize(self, model):
        """
        According to weights' and activations' quantization types, the model will be added some fake
        quant ops, such as fake_quantize_dequantize_moving_average_abs_max, fake_quantize_dequantize_abs_max
        and so on.

        Args:
            model(fluid.dygraph.Layer): the model to be quantized.
        Returns:
            None
        """
        for name, layer in model.named_sublayers():
            if not isinstance(layer, self._quantizable_layer_type):
                continue

            scopes = name.split('.')
            target = scopes[-1]
            obj = model
            parent = model
            for i in range(len(scopes) - 1):
                obj = getattr(parent, scopes[i])
                parent = obj

            quant_layer = self._get_quantized_counterpart(layer)
            setattr(obj, target, quant_layer)

    def _get_quantized_counterpart(self, layer):
        quant_layers = tuple(self._quant_layers_map.values())
        quantized_counterpart = tuple('Quantized' + k
                                      for k in self._quant_layers_map.keys())

        predicate = lambda value: isinstance(layer, value)
        index_generator = (i for i, v in enumerate(quant_layers)
                           if predicate(v))

        try:
            index = next(index_generator)
        except StopIteration:
            _logger.fatal("The layer {} is unsupported to be quantized.".format(
                layer.full_name()))
            sys.exit(-1)

        quantized_layer = quant_nn.__dict__[quantized_counterpart[index]](
            layer, self._weight_bits, self._activation_bits, self._moving_rate,
            self._weight_quantize_type, self._activation_quantize_type)
        return quantized_layer
