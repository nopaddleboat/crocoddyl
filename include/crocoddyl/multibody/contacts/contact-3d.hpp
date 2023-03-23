///////////////////////////////////////////////////////////////////////////////
// BSD 3-Clause License
//
// Copyright (C) 2019-2023, LAAS-CNRS, University f_world Edinburgh,
//                          Heriot-Watt University
// Copyright note valid unless otherwise stated in individual files.
// All rights reserved.
///////////////////////////////////////////////////////////////////////////////

#ifndef CROCODDYL_MULTIBODY_CONTACTS_CONTACT_3D_HPP_
#define CROCODDYL_MULTIBODY_CONTACTS_CONTACT_3D_HPP_

#include <pinocchio/spatial/motion.hpp>
#include <pinocchio/multibody/data.hpp>
#include <pinocchio/algorithm/frames.hpp>
#include <pinocchio/algorithm/kinematics-derivatives.hpp>

#include "crocoddyl/multibody/fwd.hpp"
#include "crocoddyl/core/utils/exception.hpp"
#include "crocoddyl/multibody/contact-base.hpp"
#include "crocoddyl/core/utils/deprecate.hpp"

namespace crocoddyl {

template <typename _Scalar>
class ContactModel3DTpl : public ContactModelAbstractTpl<_Scalar> {
 public:
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  typedef _Scalar Scalar;
  typedef MathBaseTpl<Scalar> MathBase;
  typedef ContactModelAbstractTpl<Scalar> Base;
  typedef ContactData3DTpl<Scalar> Data;
  typedef StateMultibodyTpl<Scalar> StateMultibody;
  typedef ContactDataAbstractTpl<Scalar> ContactDataAbstract;
  typedef typename MathBase::Matrix3s Matrix3s;
  typedef typename MathBase::Vector2s Vector2s;
  typedef typename MathBase::Vector3s Vector3s;
  typedef typename MathBase::VectorXs VectorXs;

  /**
   * @brief Initialize the 3d contact model
   *
   * @param[in] state  State of the multibody system
   * @param[in] id     Reference frame id of the contact
   * @param[in] xref   Contact position used for the Baumgarte stabilization
   * @param[in] type   Type of contact
   * @param[in] nu     Dimension of the control vector
   * @param[in] gains  Baumgarte stabilization gains
   */
  ContactModel3DTpl(boost::shared_ptr<StateMultibody> state, const pinocchio::FrameIndex id, const Vector3s& xref,
                    const pinocchio::ReferenceFrame type, const std::size_t nu,
                    const Vector2s& gains = Vector2s::Zero());

  /**
   * @brief Initialize the 3d contact model
   *
   * The default `nu` is obtained from `StateAbstractTpl::get_nv()`.
   *
   * @param[in] state  State of the multibody system
   * @param[in] id     Reference frame id of the contact
   * @param[in] xref   Contact position used for the Baumgarte stabilization
   * @param[in] type   Type of contact
   * @param[in] gains  Baumgarte stabilization gains
   */
  ContactModel3DTpl(boost::shared_ptr<StateMultibody> state, const pinocchio::FrameIndex id, const Vector3s& xref,
                    const pinocchio::ReferenceFrame type, const Vector2s& gains = Vector2s::Zero());

  DEPRECATED("Use constructor that passes the type type of contact, this assumes is pinocchio::LOCAL",
             ContactModel3DTpl(boost::shared_ptr<StateMultibody> state, const pinocchio::FrameIndex id,
                               const Vector3s& xref, const std::size_t nu, const Vector2s& gains = Vector2s::Zero());)
  DEPRECATED("Use constructor that passes the type type of contact, this assumes is pinocchio::LOCAL",
             ContactModel3DTpl(boost::shared_ptr<StateMultibody> state, const pinocchio::FrameIndex id,
                               const Vector3s& xref, const Vector2s& gains = Vector2s::Zero());)
  virtual ~ContactModel3DTpl();

  /**
   * @brief Compute the 3d contact Jacobian and drift
   *
   * @param[in] data  3d contact data
   * @param[in] x     State point \f$\mathbf{x}\in\mathbb{R}^{ndx}\f$
   * @param[in] u     Control input \f$\mathbf{u}\in\mathbb{R}^{nu}\f$
   */
  virtual void calc(const boost::shared_ptr<ContactDataAbstract>& data, const Eigen::Ref<const VectorXs>& x);

  /**
   * @brief Compute the derivatives of the 3d contact holonomic constraint
   *
   * @param[in] data  3d contact data
   * @param[in] x     State point \f$\mathbf{x}\in\mathbb{R}^{ndx}\f$
   * @param[in] u     Control input \f$\mathbf{u}\in\mathbb{R}^{nu}\f$
   */
  virtual void calcDiff(const boost::shared_ptr<ContactDataAbstract>& data, const Eigen::Ref<const VectorXs>& x);

  /**
   * @brief Convert the force into a stack of spatial forces
   *
   * @param[in] data   3d contact data
   * @param[in] force  3d force
   */
  virtual void updateForce(const boost::shared_ptr<ContactDataAbstract>& data, const VectorXs& force);

  /**
   * @brief Create the 3d contact data
   */
  virtual boost::shared_ptr<ContactDataAbstract> createData(pinocchio::DataTpl<Scalar>* const data);

  /**
   * @brief Return the reference frame translation
   */
  const Vector3s& get_reference() const;

  /**
   * @brief Return the Baumgarte stabilization gains
   */
  const Vector2s& get_gains() const;

  /**
   * @brief Modify the reference frame translation
   */
  void set_reference(const Vector3s& reference);

  /**
   * @brief Print relevant information of the 3d contact model
   *
   * @param[out] os  Output stream object
   */
  virtual void print(std::ostream& os) const;

 protected:
  using Base::id_;
  using Base::nc_;
  using Base::nu_;
  using Base::state_;
  using Base::type_;

 private:
  Vector3s xref_;   //!< Contact position used for the Baumgarte stabilization
  Vector2s gains_;  //!< Baumgarte stabilization gains
};

template <typename _Scalar>
struct ContactData3DTpl : public ContactDataAbstractTpl<_Scalar> {
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  typedef _Scalar Scalar;
  typedef MathBaseTpl<Scalar> MathBase;
  typedef ContactDataAbstractTpl<Scalar> Base;
  typedef typename MathBase::Vector3s Vector3s;
  typedef typename MathBase::Matrix3s Matrix3s;
  typedef typename MathBase::Matrix3xs Matrix3xs;
  typedef typename MathBase::Matrix6xs Matrix6xs;
  typedef typename pinocchio::MotionTpl<Scalar> Motion;
  typedef typename pinocchio::ForceTpl<Scalar> Force;

  template <template <typename Scalar> class Model>
  ContactData3DTpl(Model<Scalar>* const model, pinocchio::DataTpl<Scalar>* const data)
      : Base(model, data),
        v(Motion::Zero()),
        f_local(Force::Zero()),
        da0_local_dx(3, model->get_state()->get_ndx()),
        fJf(6, model->get_state()->get_nv()),
        v_partial_dq(6, model->get_state()->get_nv()),
        a_partial_dq(6, model->get_state()->get_nv()),
        a_partial_dv(6, model->get_state()->get_nv()),
        a_partial_da(6, model->get_state()->get_nv()),
        fXjdv_dq(6, model->get_state()->get_nv()),
        fXjda_dq(6, model->get_state()->get_nv()),
        fXjda_dv(6, model->get_state()->get_nv()),
        fJf_df(3, model->get_state()->get_nv()) {
    frame = model->get_id();
    jMf = model->get_state()->get_pinocchio()->frames[frame].placement;
    fXj = jMf.inverse().toActionMatrix();
    a0_local.setZero();
    dp.setZero();
    dp_local.setZero();
    da0_local_dx.setZero();
    fJf.setZero();
    v_partial_dq.setZero();
    a_partial_dq.setZero();
    a_partial_dv.setZero();
    a_partial_da.setZero();
    vv_skew.setZero();
    vw_skew.setZero();
    a0_skew.setZero();
    a0_world_skew.setZero();
    dp_skew.setZero();
    f_skew.setZero();
    fXjdv_dq.setZero();
    fXjda_dq.setZero();
    fXjda_dv.setZero();
    fJf_df.setZero();
  }

  using Base::a0;
  using Base::da0_dx;
  using Base::df_du;
  using Base::df_dx;
  using Base::f;
  using Base::frame;
  using Base::fXj;
  using Base::Jc;
  using Base::jMf;
  using Base::pinocchio;

  Motion v;
  Vector3s a0_local;
  Vector3s dp;
  Vector3s dp_local;
  Force f_local;
  Matrix3xs da0_local_dx;
  Matrix6xs fJf;
  Matrix6xs v_partial_dq;
  Matrix6xs a_partial_dq;
  Matrix6xs a_partial_dv;
  Matrix6xs a_partial_da;
  Matrix3s vv_skew;
  Matrix3s vw_skew;
  Matrix3s a0_skew;
  Matrix3s a0_world_skew;
  Matrix3s dp_skew;
  Matrix3s f_skew;
  Matrix6xs fXjdv_dq;
  Matrix6xs fXjda_dq;
  Matrix6xs fXjda_dv;
  Matrix3xs fJf_df;
};

}  // namespace crocoddyl

/* --- Details -------------------------------------------------------------- */
/* --- Details -------------------------------------------------------------- */
/* --- Details -------------------------------------------------------------- */
#include "crocoddyl/multibody/contacts/contact-3d.hxx"

#endif  // CROCODDYL_MULTIBODY_CONTACTS_CONTACT_3D_HPP_
