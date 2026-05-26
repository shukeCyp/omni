import unittest
from unittest.mock import MagicMock, patch

from app.services.gpt_image import GptImageXiaobanshou
from app.services.media_generation import media_generation_registry


class GptImageXiaobanshouTests(unittest.TestCase):
    @patch("app.services.gpt_image.xiaobanshou.requests.post")
    def test_generate_uses_gpt_image_async_videos_contract(self, mock_post):
        service = GptImageXiaobanshou("test-key")

        response = MagicMock()
        response.status_code = 200
        response.text = '{"id":"gpt_img_123","status":"completed","video_url":"data:image/png;base64,QUJD"}'
        response.json.return_value = {
            "id": "gpt_img_123",
            "status": "completed",
            "video_url": "data:image/png;base64,QUJD",
        }
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        result = service.generate("white dog", aspect_ratio="16:9")

        self.assertTrue(result.success)
        self.assertEqual(result.mime_type, "image/png")
        self.assertEqual(result.image_data, "QUJD")

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://xibapi.com/v1/videos")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "gpt-image-2")
        self.assertEqual(kwargs["json"]["prompt"], "white dog")
        self.assertEqual(kwargs["json"]["metadata"]["size"], "1920x1080")
        self.assertEqual(kwargs["json"]["metadata"]["urls"], [])

    @patch("app.services.gpt_image.xiaobanshou.requests.post")
    def test_generate_puts_reference_images_in_metadata_urls(self, mock_post):
        service = GptImageXiaobanshou("test-key")

        response = MagicMock()
        response.status_code = 200
        response.text = '{"video_url":"data:image/png;base64,iVBORw0KGgo="}'
        response.json.return_value = {"video_url": "data:image/png;base64,iVBORw0KGgo="}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        result = service.generate(
            "turn gray",
            aspect_ratio="9:16",
            ref_images=[{"base64": "QUJD", "mime": "image/jpeg"}],
        )

        self.assertTrue(result.success)
        self.assertEqual(result.mime_type, "image/png")

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://xibapi.com/v1/videos")
        self.assertEqual(kwargs["json"]["model"], "gpt-image-2")
        self.assertEqual(kwargs["json"]["metadata"]["size"], "1080x1920")
        self.assertEqual(kwargs["json"]["metadata"]["urls"], ["data:image/jpeg;base64,QUJD"])

    def test_registry_resolves_xiaobanshou_gpt_image_legacy_setting(self):
        generator, platform, provider = media_generation_registry.resolve_image_generator(
            {"nanobanana_model": "gpt-image:xiaobanshou", "xiaobanshou_api_key": "test-key"}
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "gpt-image")
        self.assertEqual(provider, "xiaobanshou")


if __name__ == "__main__":
    unittest.main()
