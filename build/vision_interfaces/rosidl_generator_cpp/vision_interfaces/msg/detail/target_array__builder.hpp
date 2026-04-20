// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from vision_interfaces:msg/TargetArray.idl
// generated code does not contain a copyright notice

#ifndef VISION_INTERFACES__MSG__DETAIL__TARGET_ARRAY__BUILDER_HPP_
#define VISION_INTERFACES__MSG__DETAIL__TARGET_ARRAY__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "vision_interfaces/msg/detail/target_array__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace vision_interfaces
{

namespace msg
{

namespace builder
{

class Init_TargetArray_targets
{
public:
  Init_TargetArray_targets()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::vision_interfaces::msg::TargetArray targets(::vision_interfaces::msg::TargetArray::_targets_type arg)
  {
    msg_.targets = std::move(arg);
    return std::move(msg_);
  }

private:
  ::vision_interfaces::msg::TargetArray msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::vision_interfaces::msg::TargetArray>()
{
  return vision_interfaces::msg::builder::Init_TargetArray_targets();
}

}  // namespace vision_interfaces

#endif  // VISION_INTERFACES__MSG__DETAIL__TARGET_ARRAY__BUILDER_HPP_
