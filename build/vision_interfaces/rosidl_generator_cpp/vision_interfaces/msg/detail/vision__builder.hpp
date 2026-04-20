// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from vision_interfaces:msg/Vision.idl
// generated code does not contain a copyright notice

#ifndef VISION_INTERFACES__MSG__DETAIL__VISION__BUILDER_HPP_
#define VISION_INTERFACES__MSG__DETAIL__VISION__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "vision_interfaces/msg/detail/vision__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace vision_interfaces
{

namespace msg
{

namespace builder
{

class Init_Vision_shape
{
public:
  explicit Init_Vision_shape(::vision_interfaces::msg::Vision & msg)
  : msg_(msg)
  {}
  ::vision_interfaces::msg::Vision shape(::vision_interfaces::msg::Vision::_shape_type arg)
  {
    msg_.shape = std::move(arg);
    return std::move(msg_);
  }

private:
  ::vision_interfaces::msg::Vision msg_;
};

class Init_Vision_color
{
public:
  explicit Init_Vision_color(::vision_interfaces::msg::Vision & msg)
  : msg_(msg)
  {}
  Init_Vision_shape color(::vision_interfaces::msg::Vision::_color_type arg)
  {
    msg_.color = std::move(arg);
    return Init_Vision_shape(msg_);
  }

private:
  ::vision_interfaces::msg::Vision msg_;
};

class Init_Vision_number
{
public:
  explicit Init_Vision_number(::vision_interfaces::msg::Vision & msg)
  : msg_(msg)
  {}
  Init_Vision_color number(::vision_interfaces::msg::Vision::_number_type arg)
  {
    msg_.number = std::move(arg);
    return Init_Vision_color(msg_);
  }

private:
  ::vision_interfaces::msg::Vision msg_;
};

class Init_Vision_y
{
public:
  explicit Init_Vision_y(::vision_interfaces::msg::Vision & msg)
  : msg_(msg)
  {}
  Init_Vision_number y(::vision_interfaces::msg::Vision::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_Vision_number(msg_);
  }

private:
  ::vision_interfaces::msg::Vision msg_;
};

class Init_Vision_x
{
public:
  Init_Vision_x()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Vision_y x(::vision_interfaces::msg::Vision::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_Vision_y(msg_);
  }

private:
  ::vision_interfaces::msg::Vision msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::vision_interfaces::msg::Vision>()
{
  return vision_interfaces::msg::builder::Init_Vision_x();
}

}  // namespace vision_interfaces

#endif  // VISION_INTERFACES__MSG__DETAIL__VISION__BUILDER_HPP_
