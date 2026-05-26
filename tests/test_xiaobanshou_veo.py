import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.constants import SettingKeys
from app.services.media_generation import media_generation_registry
from app.services.veo.xiaobanshou import VeoXiaobanshou


class VeoXiaobanshouTests(unittest.TestCase):
    def setUp(self):
        self.service = VeoXiaobanshou("test-key")

    @patch("app.services.veo.xiaobanshou.requests.post")
    def test_submit_task_uses_multipart_contract_for_text_video(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id":"task_xbs_123","status":"queued"}'
        mock_response.json.return_value = {"id": "task_xbs_123", "status": "queued"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        task_id = self.service._submit_task(
            prompt="a cat in a garden",
            model="veo_3_1-fast",
            size="1280x720",
        )

        self.assertEqual(task_id, "task_xbs_123")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        multipart = kwargs["files"]
        self.assertIn(("model", (None, b"veo_3_1-fast", "text/plain; charset=utf-8")), multipart)
        self.assertIn(("prompt", (None, b"a cat in a garden", "text/plain; charset=utf-8")), multipart)
        self.assertIn(("size", (None, b"1280x720", "text/plain; charset=utf-8")), multipart)
        self.assertNotIn("json", kwargs)

    def test_encode_form_value_supports_chinese_prompt(self):
        self.assertEqual(self.service._encode_form_value("一只可爱的小猫"), "一只可爱的小猫".encode("utf-8"))

    @patch("app.services.veo.xiaobanshou.VeoXiaobanshou._poll_task")
    @patch("app.services.veo.xiaobanshou.requests.post")
    def test_generate_image_video_uses_fl_model_and_input_reference_array_field(self, mock_post, mock_poll_task):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id":"task_xbs_123","status":"queued"}'
        mock_response.json.return_value = {"id": "task_xbs_123", "status": "queued"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"fake-image")
            tmp.flush()
            self.service.generate(
                "animate this image",
                orientation="landscape",
                ref_image_path=tmp.name,
            )

        _, kwargs = mock_post.call_args
        multipart = kwargs["files"]
        self.assertIn(("model", (None, b"veo_3_1-fast-fl", "text/plain; charset=utf-8")), multipart)
        self.assertIn(("size", (None, b"1280x720", "text/plain; charset=utf-8")), multipart)
        file_fields = [item for item in multipart if item[0] == "input_reference[]"]
        self.assertEqual(len(file_fields), 1)
        self.assertEqual(file_fields[0][0], "input_reference[]")

    @patch("app.services.veo.xiaobanshou.requests.get")
    def test_poll_task_reads_completed_url_field(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"id":"task_xbs_123","object":"video","model":"veo_3_1-fast","status":"completed",'
            '"progress":100,"created_at":1709876543,"completed_at":1709876600,'
            '"url":"https://example.com/videos/xxx.mp4"}'
        )
        mock_response.json.return_value = {
            "id": "task_xbs_123",
            "object": "video",
            "model": "veo_3_1-fast",
            "status": "completed",
            "progress": 100,
            "created_at": 1709876543,
            "completed_at": 1709876600,
            "url": "https://example.com/videos/xxx.mp4",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.service._poll_task("task_xbs_123", timeout_seconds=1, interval_seconds=0)

        self.assertTrue(result.success)
        self.assertEqual(result.video_url, "https://example.com/videos/xxx.mp4")


class XiaobanshouVeoRegistryTests(unittest.TestCase):
    def test_resolve_video_generator_supports_veo_xiaobanshou_setting(self):
        settings = {
            "veo_model": "xiaobanshou",
            SettingKeys.XIAOBANSHOU_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(
            settings,
            platform="veo3",
            provider="",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "veo3")
        self.assertEqual(provider, "xiaobanshou")


if __name__ == "__main__":
    unittest.main()
