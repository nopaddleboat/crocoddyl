///////////////////////////////////////////////////////////////////////////////
// BSD 3-Clause License
//
// Copyright (C) 2018-2019, LAAS-CNRS
// Copyright note valid unless otherwise stated in individual files.
// All rights reserved.
///////////////////////////////////////////////////////////////////////////////

#ifndef CROCODDYL_CORE_STATES_STATE_EUCLIDEAN_HPP_
#define CROCODDYL_CORE_STATES_STATE_EUCLIDEAN_HPP_

#include "crocoddyl/core/state-base.hpp"
#include <pinocchio/multibody/model.hpp>
#include <pinocchio/multibody/data.hpp>

namespace crocoddyl {

class StateVector : public StateAbstract {
 public:
  StateVector(const unsigned int& nx);
  ~StateVector();

  Eigen::VectorXd zero();
  Eigen::VectorXd rand();
  void diff(const Eigen::Ref<const Eigen::VectorXd>& x0, const Eigen::Ref<const Eigen::VectorXd>& x1,
            Eigen::Ref<Eigen::VectorXd> dxout);
  void integrate(const Eigen::Ref<const Eigen::VectorXd>& x, const Eigen::Ref<const Eigen::VectorXd>& dx,
                 Eigen::Ref<Eigen::VectorXd> xout);
  void Jdiff(const Eigen::Ref<const Eigen::VectorXd>&, const Eigen::Ref<const Eigen::VectorXd>&,
             Eigen::Ref<Eigen::MatrixXd> Jfirst, Eigen::Ref<Eigen::MatrixXd> Jsecond, Jcomponent firstsecond = both);
  void Jintegrate(const Eigen::Ref<const Eigen::VectorXd>&, const Eigen::Ref<const Eigen::VectorXd>&,
                  Eigen::Ref<Eigen::MatrixXd> Jfirst, Eigen::Ref<Eigen::MatrixXd> Jsecond,
                  Jcomponent firstsecond = both);

 private:
  pinocchio::Model model_;
  // pinocchio::Data data_;
};

}  // namespace crocoddyl

#endif  // CROCODDYL_CORE_STATES_STATE_EUCLIDEAN_HPP_
