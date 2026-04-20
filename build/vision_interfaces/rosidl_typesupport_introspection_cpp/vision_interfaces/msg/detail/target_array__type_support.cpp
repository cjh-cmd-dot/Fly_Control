// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from vision_interfaces:msg/TargetArray.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "vision_interfaces/msg/detail/target_array__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace vision_interfaces
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void TargetArray_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) vision_interfaces::msg::TargetArray(_init);
}

void TargetArray_fini_function(void * message_memory)
{
  auto typed_message = static_cast<vision_interfaces::msg::TargetArray *>(message_memory);
  typed_message->~TargetArray();
}

size_t size_function__TargetArray__targets(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<vision_interfaces::msg::Target> *>(untyped_member);
  return member->size();
}

const void * get_const_function__TargetArray__targets(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<vision_interfaces::msg::Target> *>(untyped_member);
  return &member[index];
}

void * get_function__TargetArray__targets(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<vision_interfaces::msg::Target> *>(untyped_member);
  return &member[index];
}

void fetch_function__TargetArray__targets(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const vision_interfaces::msg::Target *>(
    get_const_function__TargetArray__targets(untyped_member, index));
  auto & value = *reinterpret_cast<vision_interfaces::msg::Target *>(untyped_value);
  value = item;
}

void assign_function__TargetArray__targets(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<vision_interfaces::msg::Target *>(
    get_function__TargetArray__targets(untyped_member, index));
  const auto & value = *reinterpret_cast<const vision_interfaces::msg::Target *>(untyped_value);
  item = value;
}

void resize_function__TargetArray__targets(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<vision_interfaces::msg::Target> *>(untyped_member);
  member->resize(size);
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember TargetArray_message_member_array[1] = {
  {
    "targets",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<vision_interfaces::msg::Target>(),  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(vision_interfaces::msg::TargetArray, targets),  // bytes offset in struct
    nullptr,  // default value
    size_function__TargetArray__targets,  // size() function pointer
    get_const_function__TargetArray__targets,  // get_const(index) function pointer
    get_function__TargetArray__targets,  // get(index) function pointer
    fetch_function__TargetArray__targets,  // fetch(index, &value) function pointer
    assign_function__TargetArray__targets,  // assign(index, value) function pointer
    resize_function__TargetArray__targets  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers TargetArray_message_members = {
  "vision_interfaces::msg",  // message namespace
  "TargetArray",  // message name
  1,  // number of fields
  sizeof(vision_interfaces::msg::TargetArray),
  TargetArray_message_member_array,  // message members
  TargetArray_init_function,  // function to initialize message memory (memory has to be allocated)
  TargetArray_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t TargetArray_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &TargetArray_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace vision_interfaces


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<vision_interfaces::msg::TargetArray>()
{
  return &::vision_interfaces::msg::rosidl_typesupport_introspection_cpp::TargetArray_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, vision_interfaces, msg, TargetArray)() {
  return &::vision_interfaces::msg::rosidl_typesupport_introspection_cpp::TargetArray_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
