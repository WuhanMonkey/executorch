# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import unittest

from typing import Any, Callable

import torch

from executorch.examples.export.utils import _CAPTURE_CONFIG, _EDGE_COMPILE_CONFIG
from executorch.examples.models import MODEL_NAME_TO_MODEL

# pyre-ignore[21]: Could not find module `executorch.extension.pybindings.portable`.
from executorch.extension.pybindings.portable import (  # @manual
    _load_for_executorch_from_buffer,
)


class ExportTest(unittest.TestCase):
    def _assert_eager_lowered_same_result(
        self,
        eager_model: torch.nn.Module,
        example_inputs,
        validation_fn: Callable[[Any, Any], bool],
    ):
        """
        Asserts that the given model has the same result as the eager mode
        lowered model, with example_inputs, validated by validation_fn, which
        takes the eager mode output and ET output, and returns True if they
        match.
        """
        import executorch.exir as exir

        edge_model = exir.capture(eager_model, example_inputs, _CAPTURE_CONFIG).to_edge(
            _EDGE_COMPILE_CONFIG
        )

        executorch_prog = edge_model.to_executorch()
        # pyre-ignore
        pte_model = _load_for_executorch_from_buffer(executorch_prog.buffer)

        with torch.no_grad():
            eager_output = eager_model(*example_inputs)
        with torch.no_grad():
            executorch_output = pte_model.run_method("forward", example_inputs)

        self.assertTrue(validation_fn(eager_output, executorch_output))

    @staticmethod
    def validate_tensor_allclose(eager_output, executorch_output):
        return torch.allclose(
            eager_output,
            executorch_output[0],
            rtol=1e-5,
            atol=1e-5,
        )

    def test_mv3_export_to_executorch(self):
        eager_model, example_inputs = MODEL_NAME_TO_MODEL["mv3"]()
        eager_model = eager_model.eval()

        self._assert_eager_lowered_same_result(
            eager_model, example_inputs, self.validate_tensor_allclose
        )

    def test_mv2_export_to_executorch(self):
        eager_model, example_inputs = MODEL_NAME_TO_MODEL["mv2"]()
        eager_model = eager_model.eval()

        self._assert_eager_lowered_same_result(
            eager_model, example_inputs, self.validate_tensor_allclose
        )

    def test_emformer_export_to_executorch(self):
        eager_model, example_inputs = MODEL_NAME_TO_MODEL["emformer"]()
        eager_model = eager_model.eval()

        validate_emformer_result = (
            lambda eager_output, executorch_output: torch.allclose(
                eager_output[0],
                executorch_output[0][0],
                rtol=1e-5,
                atol=1e-5,
            )
        )

        self._assert_eager_lowered_same_result(
            eager_model, example_inputs, validate_emformer_result
        )

    def test_vit_export_to_executorch(self):
        eager_model, example_inputs = MODEL_NAME_TO_MODEL["vit"]()
        eager_model = eager_model.eval()

        self._assert_eager_lowered_same_result(
            eager_model, example_inputs, self.validate_tensor_allclose
        )
