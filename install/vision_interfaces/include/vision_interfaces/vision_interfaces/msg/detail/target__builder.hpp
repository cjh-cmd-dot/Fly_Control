// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from vision_interfaces:msg/Target.idl
// generated code does not contain a copyright notice

#ifndef VISION_INTERFACES__MSG__DETAIL__TARGET__BUILDER_HPP_
#define VISION_INTERFACES__MSG__DETAIL__TARGET__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "vision_interfaces/msg/detail/target__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace vision_interfaces
{

namespace msg
{

namespace builder
{

class Init_Target_shape
{
public:
  explicit Init_Target_shape(::vision_interfaces::msg::Target & msg)
  : msg_(msg)
  {}
  ::vision_interfaces::msg::Target shape(::vision_interfaces::msg::Target::_shape_type arg)
  {
    msg_.shape = std::move(arg);
    return std::move(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

class Init_Target_color
{
public:
  explicit Init_Target_color(::vision_interfaces::msg::Target & msg)
  : msg_(msg)
  {}
  Init_Target_shape color(::vision_interfaces::msg::Target::_color_type arg)
  {
    msg_.color = std::move(arg);
    return Init_Target_shape(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

class Init_Target_depth
{
public:
  explicit Init_Target_depth(::vision_interfaces::msg::Target & msg)
  : msg_(msg)
  {}
  Init_Target_color depth(::vision_interfaces::msg::Target::_depth_type arg)
  {
    msg_.depth = std::move(arg);
    return Init_Target_color(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

class Init_Target_number
{
public:
  explicit Init_Target_number(::vision_interfaces::msg::Target & msg)
  : msg_(msg)
  {}
  Init_Target_depth number(::vision_interfaces::msg::Target::_number_type arg)
  {
    msg_.number = std::move(arg);
    return Init_Target_depth(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

class Init_Target_z
{
public:
  explicit Init_Target_z(::vision_interfaces::msg::Target & msg)
  : msg_(msg)
  {}
  Init_Target_number z(::vision_interfaces::msg::Target::_z_type arg)
  {
    msg_.z = std::move(arg);
    return Init_Target_number(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

class Init_Target_y
{
public:
  explicit Init_Target_y(::vision_interfaces::msg::Target & msg)
  : msg_(msg)
  {}
  Init_Target_z y(::vision_interfaces::msg::Target::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_Target_z(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

class Init_Target_x
{
public:
  Init_Target_x()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Target_y x(::vision_interfaces::msg::Target::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_Target_y(msg_);
  }

private:
  ::vision_interfaces::msg::Target msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::vision_interfaces::msg::Target>()
{
  return vision_interfaces::msg::builder::Init_Target_x();
}

}  // namespace vision_interfaces

#endif  // VISION_INTERFACES__MSG__DETAIL__TARGET__BUILDER_HPP_
