// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from vision_interfaces:msg/TargetArray.idl
// generated code does not contain a copyright notice
#include "vision_interfaces/msg/detail/target_array__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `targets`
#include "vision_interfaces/msg/detail/target__functions.h"

bool
vision_interfaces__msg__TargetArray__init(vision_interfaces__msg__TargetArray * msg)
{
  if (!msg) {
    return false;
  }
  // targets
  if (!vision_interfaces__msg__Target__Sequence__init(&msg->targets, 0)) {
    vision_interfaces__msg__TargetArray__fini(msg);
    return false;
  }
  return true;
}

void
vision_interfaces__msg__TargetArray__fini(vision_interfaces__msg__TargetArray * msg)
{
  if (!msg) {
    return;
  }
  // targets
  vision_interfaces__msg__Target__Sequence__fini(&msg->targets);
}

bool
vision_interfaces__msg__TargetArray__are_equal(const vision_interfaces__msg__TargetArray * lhs, const vision_interfaces__msg__TargetArray * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // targets
  if (!vision_interfaces__msg__Target__Sequence__are_equal(
      &(lhs->targets), &(rhs->targets)))
  {
    return false;
  }
  return true;
}

bool
vision_interfaces__msg__TargetArray__copy(
  const vision_interfaces__msg__TargetArray * input,
  vision_interfaces__msg__TargetArray * output)
{
  if (!input || !output) {
    return false;
  }
  // targets
  if (!vision_interfaces__msg__Target__Sequence__copy(
      &(input->targets), &(output->targets)))
  {
    return false;
  }
  return true;
}

vision_interfaces__msg__TargetArray *
vision_interfaces__msg__TargetArray__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  vision_interfaces__msg__TargetArray * msg = (vision_interfaces__msg__TargetArray *)allocator.allocate(sizeof(vision_interfaces__msg__TargetArray), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(vision_interfaces__msg__TargetArray));
  bool success = vision_interfaces__msg__TargetArray__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
vision_interfaces__msg__TargetArray__destroy(vision_interfaces__msg__TargetArray * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    vision_interfaces__msg__TargetArray__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
vision_interfaces__msg__TargetArray__Sequence__init(vision_interfaces__msg__TargetArray__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  vision_interfaces__msg__TargetArray * data = NULL;

  if (size) {
    data = (vision_interfaces__msg__TargetArray *)allocator.zero_allocate(size, sizeof(vision_interfaces__msg__TargetArray), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = vision_interfaces__msg__TargetArray__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        vision_interfaces__msg__TargetArray__fini(&data[i - 1]);
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
vision_interfaces__msg__TargetArray__Sequence__fini(vision_interfaces__msg__TargetArray__Sequence * array)
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
      vision_interfaces__msg__TargetArray__fini(&array->data[i]);
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

vision_interfaces__msg__TargetArray__Sequence *
vision_interfaces__msg__TargetArray__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  vision_interfaces__msg__TargetArray__Sequence * array = (vision_interfaces__msg__TargetArray__Sequence *)allocator.allocate(sizeof(vision_interfaces__msg__TargetArray__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = vision_interfaces__msg__TargetArray__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
vision_interfaces__msg__TargetArray__Sequence__destroy(vision_interfaces__msg__TargetArray__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    vision_interfaces__msg__TargetArray__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
vision_interfaces__msg__TargetArray__Sequence__are_equal(const vision_interfaces__msg__TargetArray__Sequence * lhs, const vision_interfaces__msg__TargetArray__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!vision_interfaces__msg__TargetArray__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
vision_interfaces__msg__TargetArray__Sequence__copy(
  const vision_interfaces__msg__TargetArray__Sequence * input,
  vision_interfaces__msg__TargetArray__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(vision_interfaces__msg__TargetArray);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    vision_interfaces__msg__TargetArray * data =
      (vision_interfaces__msg__TargetArray *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!vision_interfaces__msg__TargetArray__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          vision_interfaces__msg__TargetArray__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!vision_interfaces__msg__TargetArray__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
