#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "types.h"
#include "data_mgr.h"
#include "cf.h"
#include "runners/cf_parallel.h"
#include "loan_schema.h"

namespace py = pybind11;

static rrm::LoanDict py_dict_to_loan(const py::dict& d) {
    rrm::LoanDict loan;
    for (auto& [key, val] : d) {
        std::string k = py::cast<std::string>(key);
        if (py::isinstance<py::int_>(val)) {
            loan[k] = py::cast<int>(val);
        } else if (py::isinstance<py::float_>(val)) {
            loan[k] = py::cast<double>(val);
        } else {
            loan[k] = py::cast<std::string>(py::str(val));
        }
    }
    return loan;
}

class PySimEngine {
public:
    void init(const std::string& input_dir,
              const py::dict& status_to_roll_py,
              const std::string& dial_name = "",
              int n_per = 360) {

        rrm::StatusMap stm;
        for (auto& [key, val] : status_to_roll_py) {
            std::string from = py::cast<std::string>(key);
            auto to_list = py::cast<std::vector<std::string>>(val);
            stm[from] = to_list;
        }

        rrm::model::ModelSpecMap specs;
        auto default_spec = rrm::model::make_default_spec();
        for (auto& [from_s, tos] : stm) {
            for (auto& to_s : tos) {
                if (to_s == from_s) continue;
                std::string name = rrm::model::get_model_name(from_s, to_s);
                specs[name] = default_spec;
            }
        }

        dm_.init(input_dir, specs, stm, dial_name, n_per);
        n_per_ = n_per;
        dial_name_ = dial_name;
    }

    py::dict run_batch(const py::list& loans_py, int dup, int n_threads,
                       uint32_t seed0) {
        std::vector<rrm::LoanDict> loans;
        for (auto& item : loans_py) {
            loans.push_back(py_dict_to_loan(py::cast<py::dict>(item)));
        }

        auto result = rrm::runners::run_batch(
            loans, dm_, n_per_, dup, n_threads, seed0, dial_name_);

        int rows = static_cast<int>(result.cf_sum.size());
        int cols = rrm::CF_COL_LEN;
        py::array_t<double> arr({rows, cols});
        auto buf = arr.mutable_unchecked<2>();
        for (int r = 0; r < rows; ++r)
            for (int c = 0; c < cols; ++c)
                buf(r, c) = result.cf_sum[r][c];

        py::dict out;
        out["cf_sum"] = arr;
        out["n_done"] = result.n_done;
        out["n_error"] = result.n_error;
        out["errors"] = result.errors;
        out["cf_col"] = rrm::CF_COL;
        return out;
    }

private:
    rrm::DataMgr dm_;
    int n_per_ = 360;
    std::string dial_name_;
};

PYBIND11_MODULE(_simengine, m) {
    m.attr("__version__") = "0.1.0";

    py::class_<PySimEngine>(m, "SimEngine")
        .def(py::init<>())
        .def("init", &PySimEngine::init,
             py::arg("input_dir"),
             py::arg("status_to_roll"),
             py::arg("dial_name") = "",
             py::arg("n_per") = 360)
        .def("run_batch", &PySimEngine::run_batch,
             py::arg("loans"),
             py::arg("dup") = 1,
             py::arg("n_threads") = 4,
             py::arg("seed0") = 42);
}
