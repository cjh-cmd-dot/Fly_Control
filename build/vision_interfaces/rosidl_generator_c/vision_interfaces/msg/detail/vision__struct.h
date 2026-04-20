// NOLINT: This file starts with a BOM since it contain non-ASCII characters
// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from vision_interfaces:msg/Vision.idl
// generated code does not contain a copyright notice

#ifndef VISION_INTERFACES__MSG__DETAIL__VISION__STRUCT_H_
#define VISION_INTERFACES__MSG__DETAIL__VISION__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'color'
// Member 'shape'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/Vision in the package vision_interfaces.
/**
  * x,y,坐标
 */
typedef struct vision_interfaces__msg__Vision
{
  float x;
  float y;
  /// 图像序号
  float number;
  /// 图像深度
  rosidl_runtime_c__String color;
  rosidl_runtime_c__String shape;
} vision_interfaces__msg__Vision;

// Struct for a sequence of vision_interfaces__msg__Vision.
typedef struct vision_interfaces__msg__Vision__Sequence
{
  vision_interfaces__msg__Vision * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} vision_interfaces__msg__Vision__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // VISION_INTERFACES__MSG__DETAIL__VISION__STRUCT_H_
