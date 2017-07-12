/* Copyright (c) 2016 PaddlePaddle Authors. All Rights Reserve.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. */

#pragma once
#include "paddle/framework/enforce.h"
#include "paddle/platform/device.h"
#include "unsupported/Eigen/CXX11/Tensor"
#ifndef PADDLE_ONLY_CPU
#include "paddle/platform/cuda_device.h"
#endif

namespace paddle {
namespace platform {

struct DeviceContext {
  void* device_context{nullptr};

  template <typename DeviceType>
  inline paddle::platform::Device<DeviceType>* device_context() {
    return static_cast<paddle::platform::Device<DeviceType>*>(device_context);
  }
};

}  // namespace platform
}  // namespace paddle
