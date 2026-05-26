import unittest
import tempfile
from unittest.mock import MagicMock, patch

from app.services.veo.bandianwa import VeoBandianwa


class VeoBandianwaTests(unittest.TestCase):
    def setUp(self):
        self.service = VeoBandianwa("test-key")

    @patch("app.services.veo.bandianwa.requests.post")
    def test_submit_task_serializes_seconds_as_string(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"task_id":"task_123"}'
        mock_response.json.return_value = {"task_id": "task_123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        task_id = self.service._submit_task(
            {
                "model": "veo_3_1-fast-portrait",
                "prompt": "make a video",
                "seconds": "10",
            }
        )

        self.assertEqual(task_id, "task_123")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"]["seconds"], "10")

    @patch("app.services.veo.bandianwa.VeoBandianwa._poll_task")
    @patch("app.services.veo.bandianwa.VeoBandianwa._submit_task")
    def test_generate_uses_string_seconds_in_payload(self, mock_submit_task, mock_poll_task):
        mock_submit_task.return_value = "task_123"
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        self.service.generate("make a video", duration=10)

        payload = mock_submit_task.call_args.args[0]
        self.assertEqual(payload["seconds"], "10")

    @patch("app.services.veo.bandianwa.VeoBandianwa._poll_task")
    @patch("app.services.veo.bandianwa.VeoBandianwa._submit_task")
    def test_generate_uses_standard_model_for_text_video(self, mock_submit_task, mock_poll_task):
        mock_submit_task.return_value = "task_123"
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        self.service.generate("make a video", orientation="landscape")

        payload = mock_submit_task.call_args.args[0]
        self.assertEqual(payload["model"], "veo_3_1-fast-landscape")

    @patch("app.services.veo.bandianwa.VeoBandianwa._poll_task")
    @patch("app.services.veo.bandianwa.VeoBandianwa._submit_task")
    def test_generate_uses_hd_fl_model_for_image_video(self, mock_submit_task, mock_poll_task):
        mock_submit_task.return_value = "task_123"
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"fake-image")
            tmp.flush()
            self.service.generate(
                "make a video",
                orientation="landscape",
                ref_image_path=tmp.name,
            )

        payload = mock_submit_task.call_args.args[0]
        self.assertEqual(payload["model"], "veo_3_1-fast-landscape-fl-hd")
        self.assertIn("input_reference", payload)


if __name__ == "__main__":
    unittest.main()
