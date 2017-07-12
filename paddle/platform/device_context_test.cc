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

#include "paddle/platform/device_context.h"
#include "gtest/gtest.h"

TEST(DeviceContext, Init) {
  int count = paddle::platform::GetDeviceCount();
  for (int i = 0; i < count; i++) {
    paddle::platform::Device<DEVICE_GPU>* device =
        new paddle::platform::Device<DEVICE_GPU>(i);
    paddle::platform::DeviceContext context;
    context.device_context = device;
    Eigen::GpuDevice gpu_device =
        context.device_context<DEVICE_GPU>->eigen_device();
    ASSERT_NE(nullptr, gpu_device.stream());
    delete device;
  }
}