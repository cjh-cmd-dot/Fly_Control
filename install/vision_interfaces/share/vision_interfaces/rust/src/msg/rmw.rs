#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "vision_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__vision_interfaces__msg__Target() -> *const std::ffi::c_void;
}

#[link(name = "vision_interfaces__rosidl_generator_c")]
extern "C" {
    fn vision_interfaces__msg__Target__init(msg: *mut Target) -> bool;
    fn vision_interfaces__msg__Target__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Target>, size: usize) -> bool;
    fn vision_interfaces__msg__Target__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Target>);
    fn vision_interfaces__msg__Target__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Target>, out_seq: *mut rosidl_runtime_rs::Sequence<Target>) -> bool;
}

// Corresponds to vision_interfaces__msg__Target
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// x,y,z坐标

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Target {

    // This member is not documented.
    #[allow(missing_docs)]
    pub x: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub y: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub z: f32,

    /// 图像序号
    pub number: f32,

    /// 图像深度
    pub depth: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub color: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub shape: rosidl_runtime_rs::String,

}



impl Default for Target {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !vision_interfaces__msg__Target__init(&mut msg as *mut _) {
        panic!("Call to vision_interfaces__msg__Target__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Target {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__Target__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__Target__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__Target__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Target {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Target where Self: Sized {
  const TYPE_NAME: &'static str = "vision_interfaces/msg/Target";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__vision_interfaces__msg__Target() }
  }
}


#[link(name = "vision_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__vision_interfaces__msg__TargetArray() -> *const std::ffi::c_void;
}

#[link(name = "vision_interfaces__rosidl_generator_c")]
extern "C" {
    fn vision_interfaces__msg__TargetArray__init(msg: *mut TargetArray) -> bool;
    fn vision_interfaces__msg__TargetArray__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<TargetArray>, size: usize) -> bool;
    fn vision_interfaces__msg__TargetArray__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<TargetArray>);
    fn vision_interfaces__msg__TargetArray__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<TargetArray>, out_seq: *mut rosidl_runtime_rs::Sequence<TargetArray>) -> bool;
}

// Corresponds to vision_interfaces__msg__TargetArray
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct TargetArray {

    // This member is not documented.
    #[allow(missing_docs)]
    pub targets: rosidl_runtime_rs::Sequence<super::super::msg::rmw::Target>,

}



impl Default for TargetArray {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !vision_interfaces__msg__TargetArray__init(&mut msg as *mut _) {
        panic!("Call to vision_interfaces__msg__TargetArray__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for TargetArray {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__TargetArray__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__TargetArray__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__TargetArray__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for TargetArray {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for TargetArray where Self: Sized {
  const TYPE_NAME: &'static str = "vision_interfaces/msg/TargetArray";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__vision_interfaces__msg__TargetArray() }
  }
}


#[link(name = "vision_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__vision_interfaces__msg__Vision() -> *const std::ffi::c_void;
}

#[link(name = "vision_interfaces__rosidl_generator_c")]
extern "C" {
    fn vision_interfaces__msg__Vision__init(msg: *mut Vision) -> bool;
    fn vision_interfaces__msg__Vision__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<Vision>, size: usize) -> bool;
    fn vision_interfaces__msg__Vision__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<Vision>);
    fn vision_interfaces__msg__Vision__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<Vision>, out_seq: *mut rosidl_runtime_rs::Sequence<Vision>) -> bool;
}

// Corresponds to vision_interfaces__msg__Vision
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// x,y,坐标

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Vision {

    // This member is not documented.
    #[allow(missing_docs)]
    pub x: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub y: f32,

    /// 图像序号
    pub number: f32,

    /// 图像深度
    pub color: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub shape: rosidl_runtime_rs::String,

}



impl Default for Vision {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !vision_interfaces__msg__Vision__init(&mut msg as *mut _) {
        panic!("Call to vision_interfaces__msg__Vision__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for Vision {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__Vision__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__Vision__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { vision_interfaces__msg__Vision__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for Vision {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for Vision where Self: Sized {
  const TYPE_NAME: &'static str = "vision_interfaces/msg/Vision";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__vision_interfaces__msg__Vision() }
  }
}


