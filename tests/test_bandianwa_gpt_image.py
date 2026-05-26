import unittest
from unittest.mock import MagicMock, patch

from app.services.gpt_image import GptImageBandianwa
from app.services.media_generation import media_generation_registry


class GptImageBandianwaTests(unittest.TestCase):
    @patch("app.services.gpt_image.bandianwa.requests.get")
    @patch("app.services.gpt_image.bandianwa.requests.post")
    def test_generate_uses_auto_image_contract(self, mock_post, mock_get):
        service = GptImageBandianwa("test-key")

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.text = '{"task_id":"task_123"}'
        submit_response.json.return_value = {"task_id": "task_123"}
        submit_response.raise_for_status.return_value = None
        mock_post.return_value = submit_response

        query_response = MagicMock()
        query_response.status_code = 200
        query_response.text = '{"status":"completed","data":[{"url":"data:image/png;base64,QUJD"}]}'
        query_response.json.return_value = {
            "status": "completed",
            "data": [{"url": "data:image/png;base64,QUJD"}],
        }
        query_response.raise_for_status.return_value = None
        mock_get.return_value = query_response

        result = service.generate("white dog", aspect_ratio="16:9")

        self.assertTrue(result.success)
        self.assertEqual(result.mime_type, "image/png")
        self.assertEqual(result.image_data, "QUJD")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "auto-image")
        self.assertEqual(kwargs["json"]["prompt"], "white dog")
        self.assertEqual(kwargs["json"]["response_format"], "url")
        self.assertEqual(kwargs["json"]["size"], "1920x1080")
        self.assertNotIn("image", kwargs["json"])

    def test_resolve_size_uses_exact_aspect_ratios(self):
        self.assertEqual(GptImageBandianwa._resolve_size("1:1"), "1024x1024")
        self.assertEqual(GptImageBandianwa._resolve_size("16:9"), "1920x1080")
        self.assertEqual(GptImageBandianwa._resolve_size("9:16"), "1080x1920")
        self.assertEqual(GptImageBandianwa._resolve_size("4:3"), "1536x1152")
        self.assertEqual(GptImageBandianwa._resolve_size("3:4"), "1152x1536")

    @patch("app.services.gpt_image.bandianwa.requests.get")
    @patch("app.services.gpt_image.bandianwa.requests.post")
    def test_generate_uploads_base64_reference_as_url_array(self, mock_post, mock_get):
        service = GptImageBandianwa("test-key")

        upload_response = MagicMock()
        upload_response.status_code = 200
        upload_response.text = '{"data":{"url":"https://cdn.example/ref.png"}}'
        upload_response.json.return_value = {"data": {"url": "https://cdn.example/ref.png"}}
        upload_response.raise_for_status.return_value = None

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.text = '{"task_id":"task_123"}'
        submit_response.json.return_value = {"task_id": "task_123"}
        submit_response.raise_for_status.return_value = None

        mock_post.side_effect = [upload_response, submit_response]

        query_response = MagicMock()
        query_response.status_code = 200
        query_response.text = '{"status":"completed","data":[{"url":"data:image/png;base64,QUJD"}]}'
        query_response.json.return_value = {
            "status": "completed",
            "data": [{"url": "data:image/png;base64,QUJD"}],
        }
        query_response.raise_for_status.return_value = None
        mock_get.return_value = query_response

        result = service.generate(
            "magazine cover",
            ref_images=[{"base64": "QUJD", "mime": "image/png"}],
        )

        self.assertTrue(result.success)
        self.assertEqual(mock_post.call_count, 2)

        _, submit_kwargs = mock_post.call_args
        self.assertEqual(submit_kwargs["json"]["image"], ["https://cdn.example/ref.png"])

    def test_registry_resolves_gpt_image_legacy_setting(self):
        generator, platform, provider = media_generation_registry.resolve_image_generator(
            {"nanobanana_model": "gpt-image:bandianwa", "bandianwa_api_key": "test-key"}
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "gpt-image")
        self.assertEqual(provider, "bandianwa")


if __name__ == "__main__":
    unittest.main()
