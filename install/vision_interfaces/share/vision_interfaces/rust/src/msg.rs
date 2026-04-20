#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to vision_interfaces__msg__Target
/// x,y,z坐标

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    pub color: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub shape: std::string::String,

}



impl Default for Target {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::Target::default())
  }
}

impl rosidl_runtime_rs::Message for Target {
  type RmwMsg = super::msg::rmw::Target;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        x: msg.x,
        y: msg.y,
        z: msg.z,
        number: msg.number,
        depth: msg.depth,
        color: msg.color.as_str().into(),
        shape: msg.shape.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      x: msg.x,
      y: msg.y,
      z: msg.z,
      number: msg.number,
      depth: msg.depth,
        color: msg.color.as_str().into(),
        shape: msg.shape.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      x: msg.x,
      y: msg.y,
      z: msg.z,
      number: msg.number,
      depth: msg.depth,
      color: msg.color.to_string(),
      shape: msg.shape.to_string(),
    }
  }
}


// Corresponds to vision_interfaces__msg__TargetArray

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct TargetArray {

    // This member is not documented.
    #[allow(missing_docs)]
    pub targets: Vec<super::msg::Target>,

}



impl Default for TargetArray {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::TargetArray::default())
  }
}

impl rosidl_runtime_rs::Message for TargetArray {
  type RmwMsg = super::msg::rmw::TargetArray;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        targets: msg.targets
          .into_iter()
          .map(|elem| super::msg::Target::into_rmw_message(std::borrow::Cow::Owned(elem)).into_owned())
          .collect(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        targets: msg.targets
          .iter()
          .map(|elem| super::msg::Target::into_rmw_message(std::borrow::Cow::Borrowed(elem)).into_owned())
          .collect(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      targets: msg.targets
          .into_iter()
          .map(super::msg::Target::from_rmw_message)
          .collect(),
    }
  }
}


// Corresponds to vision_interfaces__msg__Vision
/// x,y,坐标

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    pub color: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub shape: std::string::String,

}



impl Default for Vision {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::Vision::default())
  }
}

impl rosidl_runtime_rs::Message for Vision {
  type RmwMsg = super::msg::rmw::Vision;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        x: msg.x,
        y: msg.y,
        number: msg.number,
        color: msg.color.as_str().into(),
        shape: msg.shape.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      x: msg.x,
      y: msg.y,
      number: msg.number,
        color: msg.color.as_str().into(),
        shape: msg.shape.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      x: msg.x,
      y: msg.y,
      number: msg.number,
      color: msg.color.to_string(),
      shape: msg.shape.to_string(),
    }
  }
}


