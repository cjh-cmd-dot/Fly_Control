// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from vision_interfaces:msg/TargetArray.idl
// generated code does not contain a copyright notice

#ifndef VISION_INTERFACES__MSG__DETAIL__TARGET_ARRAY__STRUCT_H_
#define VISION_INTERFACES__MSG__DETAIL__TARGET_ARRAY__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'targets'
#include "vision_interfaces/msg/detail/target__struct.h"

/// Struct defined in msg/TargetArray in the package vision_interfaces.
typedef struct vision_interfaces__msg__TargetArray
{
  vision_interfaces__msg__Target__Sequence targets;
} vision_interfaces__msg__TargetArray;

// Struct for a sequence of vision_interfaces__msg__TargetArray.
typedef struct vision_interfaces__msg__TargetArray__Sequence
{
  vision_interfaces__msg__TargetArray * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} vision_interfaces__msg__TargetArray__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // VISION_INTERFACES__MSG__DETAIL__TARGET_ARRAY__STRUCT_H_
