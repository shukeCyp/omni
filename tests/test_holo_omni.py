import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.api import Api
from app.constants import SettingKeys
from app.services.media_generation import (
    CloudyOmniGenerator,
    VideoGenerationRequest,
    media_generation_registry,
)
from app.services.omni.cloudy import OmniCloudy


class OmniRegistryTests(unittest.TestCase):
    def test_resolve_omni_defaults_to_holo_cloudy(self):
        settings = {
            SettingKeys.HOLO_VEO_API_KEY: "holo-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(
            settings,
            platform="omni",
            provider="",
        )

        self.assertIsInstance(generator, CloudyOmniGenerator)
        self.assertEqual(platform, "omni")
        self.assertEqual(provider, "cloudy")


class OmniCloudyPayloadTests(unittest.TestCase):
    def setUp(self):
        self.service = OmniCloudy("holo-key")

    @patch("app.services.omni.cloudy.OmniCloudy._poll_task")
    @patch("app.services.omni.cloudy.requests.post")
    def test_generate_text_to_video_submits_omni_flash_payload(self, mock_post, mock_poll_task):
        response = MagicMock()
        response.status_code = 202
        response.text = '{"task_id":"task_123"}'
        response.json.return_value = {"task_id": "task_123"}
        response.raise_for_status.return_value = None
        mock_post.return_value = response
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        self.service.generate(
            "show a lotus pond at sunrise",
            orientation="landscape",
            duration=6,
            resolution="4K",
            mode="text",
        )

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["model"], "omni_flash_6s_4k")
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertEqual(payload["messages"][0]["content"], "show a lotus pond at sunrise")

    @patch("app.services.omni.cloudy.OmniCloudy._poll_task")
    @patch("app.services.omni.cloudy.requests.post")
    def test_generate_components_submits_reference_images(self, mock_post, mock_poll_task):
        response = MagicMock()
        response.status_code = 202
        response.text = '{"task_id":"task_123"}'
        response.json.return_value = {"task_id": "task_123"}
        response.raise_for_status.return_value = None
        mock_post.return_value = response
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        image_paths = []
        try:
            for _ in range(3):
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.write(b"fake-image")
                tmp.close()
                image_paths.append(tmp.name)

            self.service.generate(
                "show the product",
                orientation="portrait",
                duration=10,
                resolution="720P",
                ref_image_paths=image_paths,
                mode="components",
            )
        finally:
            for path in image_paths:
                os.remove(path)

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["model"], "omni_flash_components_10s")
        self.assertEqual(payload["aspect_ratio"], "9:16")
        content = payload["messages"][0]["content"]
        image_parts = [part for part in content if part.get("type") == "image_url"]
        self.assertEqual(len(image_parts), 3)
        self.assertTrue(image_parts[0]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(content[-1], {"type": "text", "text": "show the product"})

    @patch("app.services.omni.cloudy.OmniCloudy._poll_task")
    @patch("app.services.omni.cloudy.requests.post")
    def test_generate_edit_submits_input_video_and_seconds(self, mock_post, mock_poll_task):
        response = MagicMock()
        response.status_code = 202
        response.text = '{"task_id":"task_123"}'
        response.json.return_value = {"task_id": "task_123"}
        response.raise_for_status.return_value = None
        mock_post.return_value = response
        mock_poll_task.return_value = MagicMock(success=False, error_message="stop")

        self.service.generate(
            "make the video warmer",
            orientation="portrait",
            duration=8,
            resolution="1080P",
            input_video="https://example.com/source.mp4",
            mode="edit",
        )

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["model"], "omni_flash_edit_1080p")
        self.assertEqual(payload["input_video"], "https://example.com/source.mp4")
        self.assertEqual(payload["seconds"], 8)
        self.assertEqual(payload["aspect_ratio"], "9:16")
        self.assertEqual(payload["messages"][0]["content"], "make the video warmer")

    @patch("app.services.omni.cloudy.requests.post")
    def test_components_rejects_more_than_three_reference_images_without_posting(self, mock_post):
        result = self.service.generate(
            "prompt",
            ref_image_paths=["a", "b", "c", "d"],
            mode="components",
        )

        self.assertFalse(result.success)
        self.assertIn("最多支持 3 张参考图", result.error_message)
        mock_post.assert_not_called()

    @patch("app.services.omni.cloudy.requests.get")
    def test_poll_task_reads_completed_file_url(self, mock_get):
        response = MagicMock()
        response.status_code = 200
        response.text = '{"status":"completed"}'
        response.json.return_value = {
            "status": "completed",
            "result": {"file_url": "/v1/tasks/task_123/file"},
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        result = self.service._poll_task("task_123", timeout_seconds=1, interval_seconds=0)

        self.assertTrue(result.success)
        self.assertEqual(result.video_url, "https://gpt.lyvideo.top/v1/tasks/task_123/file")


class OmniGeneratorAdapterTests(unittest.TestCase):
    @patch("app.services.media_generation.OmniCloudy")
    def test_cloudy_generator_passes_mode_and_input_video_to_service(self, mock_service_cls):
        service = mock_service_cls.return_value
        service.generate.return_value = MagicMock(
            success=True,
            video_url="https://example.com/omni.mp4",
            file_path="/tmp/omni.mp4",
            error_message="",
        )

        result = CloudyOmniGenerator().generate(
            VideoGenerationRequest(
                prompt="edit this",
                ref_images=[],
                orientation="portrait",
                duration=8,
                resolution="4K",
                generation_mode="edit",
                input_video="https://example.com/source.mp4",
                download_dir=Path("/tmp"),
            ),
            {
                SettingKeys.HOLO_VEO_API_KEY: "holo-key",
            },
        )

        self.assertTrue(result.success)
        service.generate.assert_called_once()
        _, kwargs = service.generate.call_args
        self.assertEqual(kwargs["mode"], "edit")
        self.assertEqual(kwargs["resolution"], "4K")
        self.assertEqual(kwargs["input_video"], "https://example.com/source.mp4")


class OmniDownloadTests(unittest.TestCase):
    @patch("app.api.get_media_download_dir")
    @patch("app.api.get_setting")
    @patch("requests.get")
    def test_download_veo_video_adds_holo_authorization_for_cloudy_task_file(
        self, mock_get, mock_get_setting, mock_download_dir
    ):
        mock_get_setting.side_effect = lambda key: {
            SettingKeys.HOLO_VEO_API_KEY: "holo-key",
        }.get(key, "")
        download_dir = tempfile.TemporaryDirectory()
        self.addCleanup(download_dir.cleanup)
        mock_download_dir.return_value = Path(download_dir.name)

        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        response.raise_for_status.return_value = None
        response.iter_content.return_value = [b"video-bytes"]
        mock_get.return_value = response

        result = Api().download_veo_video(
            "https://gpt.lyvideo.top/v1/tasks/task_123/file"
        )

        self.assertTrue(result["ok"])
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer holo-key")


if __name__ == "__main__":
    unittest.main()
