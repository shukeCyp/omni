import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.constants import SettingKeys
from app.services.media_generation import ZygVeoGenerator, media_generation_registry
from app.services.veo.zyg import VeoZyg


class VeoZygTests(unittest.TestCase):
    def setUp(self):
        self.service = VeoZyg("test-key")

    @patch("app.services.veo.zyg.requests.post")
    def test_submit_task_uses_multipart_contract_for_text_video(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id":"task_zyg_123","status":"queued"}'
        mock_response.json.return_value = {"id": "task_zyg_123", "status": "queued"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        task_id = self.service._submit_task(
            prompt="a cat in a garden",
            model="veo_3_1-fast",
            size="1280x720",
        )

        self.assertEqual(task_id, "task_zyg_123")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertIn("multipart/form-data; boundary=", kwargs["headers"]["Content-Type"])
        body = kwargs["data"]
        self.assertIsInstance(body, bytes)
        self.assertIn(b'name="model"', body)
        self.assertIn(b"veo_3_1-fast", body)
        self.assertIn(b'name="prompt"', body)
        self.assertIn(b"a cat in a garden", body)
        self.assertIn(b'name="size"', body)
        self.assertIn(b"1280x720", body)
        self.assertNotIn("json", kwargs)
        self.assertNotIn("files", kwargs)

    def test_encode_form_value_supports_chinese_prompt(self):
        self.assertEqual(self.service._encode_form_value("一只可爱的小猫"), "一只可爱的小猫".encode("utf-8"))

    @patch("app.services.veo.zyg.VeoZyg._poll_task")
    @patch("app.services.veo.zyg.requests.post")
    def test_generate_image_video_uses_fl_model_and_input_reference_array_field(self, mock_post, mock_poll_task):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id":"task_zyg_123","status":"queued"}'
        mock_response.json.return_value = {"id": "task_zyg_123", "status": "queued"}
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
        body = kwargs["data"]
        self.assertIn(b"veo_3_1-fast-fl", body)
        self.assertIn(b'Content-Disposition: form-data; name="input_reference[]";', body)

    def test_build_multipart_body_supports_chinese_prompt(self):
        body, content_type = self.service._build_multipart_body(
            fields=[
                ("model", "veo_3_1-fast"),
                ("prompt", "一只可爱的小猫"),
                ("size", "720x1280"),
            ]
        )

        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertIn("一只可爱的小猫".encode("utf-8"), body)

    @patch("app.services.veo.zyg.requests.get")
    def test_poll_task_reads_completed_url_field(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"id":"task_zyg_123","object":"video","model":"veo_3_1-fast","status":"completed",'
            '"progress":100,"created_at":1709876543,"completed_at":1709876600,'
            '"url":"https://example.com/videos/xxx.mp4"}'
        )
        mock_response.json.return_value = {
            "id": "task_zyg_123",
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

        result = self.service._poll_task("task_zyg_123", timeout_seconds=1, interval_seconds=0)

        self.assertTrue(result.success)
        self.assertEqual(result.video_url, "https://example.com/videos/xxx.mp4")


class ZygVeoRegistryTests(unittest.TestCase):
    def test_resolve_video_generator_supports_veo_zyg_setting(self):
        settings = {
            "veo_model": "zyg",
            SettingKeys.ZYG_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(
            settings,
            platform="veo3",
            provider="",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "veo3")
        self.assertEqual(provider, "zyg")


class ZygVeoGeneratorValidationTests(unittest.TestCase):
    def test_generate_rejects_non_ascii_api_key(self):
        generator = ZygVeoGenerator()
        result = generator.generate(
            request=MagicMock(
                prompt="test",
                ref_images=[],
                orientation="portrait",
                duration=10,
                download_dir=None,
            ),
            settings={
                SettingKeys.ZYG_API_KEY: "nano_banana_pro\tPro 版，标准分辨率",
            },
        )

        self.assertFalse(result.success)
        self.assertIn("ZYG API Key 配置异常", result.error_message)


if __name__ == "__main__":
    unittest.main()
