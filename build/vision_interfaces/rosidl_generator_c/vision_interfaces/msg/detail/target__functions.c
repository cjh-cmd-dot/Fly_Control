// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from vision_interfaces:msg/Target.idl
// generated code does not contain a copyright notice
#include "vision_interfaces/msg/detail/target__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `color`
// Member `shape`
#include "rosidl_runtime_c/string_functions.h"

bool
vision_interfaces__msg__Target__init(vision_interfaces__msg__Target * msg)
{
  if (!msg) {
    return false;
  }
  // x
  // y
  // z
  // number
  // depth
  // color
  if (!rosidl_runtime_c__String__init(&msg->color)) {
    vision_interfaces__msg__Target__fini(msg);
    return false;
  }
  // shape
  if (!rosidl_runtime_c__String__init(&msg->shape)) {
    vision_interfaces__msg__Target__fini(msg);
    return false;
  }
  return true;
}

void
vision_interfaces__msg__Target__fini(vision_interfaces__msg__Target * msg)
{
  if (!msg) {
    return;
  }
  // x
  // y
  // z
  // number
  // depth
  // color
  rosidl_runtime_c__String__fini(&msg->color);
  // shape
  rosidl_runtime_c__String__fini(&msg->shape);
}

bool
vision_interfaces__msg__Target__are_equal(const vision_interfaces__msg__Target * lhs, const vision_interfaces__msg__Target * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // x
  if (lhs->x != rhs->x) {
    return false;
  }
  // y
  if (lhs->y != rhs->y) {
    return false;
  }
  // z
  if (lhs->z != rhs->z) {
    return false;
  }
  // number
  if (lhs->number != rhs->number) {
    return false;
  }
  // depth
  if (lhs->depth != rhs->depth) {
    return false;
  }
  // color
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->color), &(rhs->color)))
  {
    return false;
  }
  // shape
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->shape), &(rhs->shape)))
  {
    return false;
  }
  return true;
}

bool
vision_interfaces__msg__Target__copy(
  const vision_interfaces__msg__Target * input,
  vision_interfaces__msg__Target * output)
{
  if (!input || !output) {
    return false;
  }
  // x
  output->x = input->x;
  // y
  output->y = input->y;
  // z
  output->z = input->z;
  // number
  output->number = input->number;
  // depth
  output->depth = input->depth;
  // color
  if (!rosidl_runtime_c__String__copy(
      &(input->color), &(output->color)))
  {
    return false;
  }
  // shape
  if (!rosidl_runtime_c__String__copy(
      &(input->shape), &(output->shape)))
  {
    return false;
  }
  return true;
}

vision_interfaces__msg__Target *
vision_interfaces__msg__Target__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  vision_interfaces__msg__Target * msg = (vision_interfaces__msg__Target *)allocator.allocate(sizeof(vision_interfaces__msg__Target), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(vision_interfaces__msg__Target));
  bool success = vision_interfaces__msg__Target__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
vision_interfaces__msg__Target__destroy(vision_interfaces__msg__Target * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    vision_interfaces__msg__Target__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
vision_interfaces__msg__Target__Sequence__init(vision_interfaces__msg__Target__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  vision_interfaces__msg__Target * data = NULL;

  if (size) {
    data = (vision_interfaces__msg__Target *)allocator.zero_allocate(size, sizeof(vision_interfaces__msg__Target), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = vision_interfaces__msg__Target__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        vision_interfaces__msg__Target__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
vision_interfaces__msg__Target__Sequence__fini(vision_interfaces__msg__Target__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      vision_interfaces__msg__Target__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

vision_interfaces__msg__Target__Sequence *
vision_interfaces__msg__Target__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  vision_interfaces__msg__Target__Sequence * array = (vision_interfaces__msg__Target__Sequence *)allocator.allocate(sizeof(vision_interfaces__msg__Target__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = vision_interfaces__msg__Target__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
vision_interfaces__msg__Target__Sequence__destroy(vision_interfaces__msg__Target__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    vision_interfaces__msg__Target__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
vision_interfaces__msg__Target__Sequence__are_equal(const vision_interfaces__msg__Target__Sequence * lhs, const vision_interfaces__msg__Target__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!vision_interfaces__msg__Target__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
vision_interfaces__msg__Target__Sequence__copy(
  const vision_interfaces__msg__Target__Sequence * input,
  vision_interfaces__msg__Target__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(vision_interfaces__msg__Target);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    vision_interfaces__msg__Target * data =
      (vision_interfaces__msg__Target *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!vision_interfaces__msg__Target__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          vision_interfaces__msg__Target__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!vision_interfaces__msg__Target__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
