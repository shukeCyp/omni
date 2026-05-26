import unittest
from unittest.mock import MagicMock, patch

import requests

from app.services.nanobanana.xiaobanshou import NanoBananaXiaobanshou


class NanoBananaXiaobanshouTests(unittest.TestCase):
    @patch("app.services.nanobanana.xiaobanshou.requests.post")
    def test_generate_uses_json_contract_from_docs(self, mock_post):
        service = NanoBananaXiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"images":[{"url":"data:image/png;base64,QUJD"}]}'
        mock_response.json.return_value = {
            "images": [
                {
                    "url": "data:image/png;base64,QUJD",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = service.generate(
            prompt="sunrise landscape",
            aspect_ratio="16:9",
            ref_images=[{"base64": "AAA", "mime": "image/jpeg"}],
        )

        self.assertTrue(result.success)
        self.assertEqual(result.mime_type, "image/png")
        self.assertEqual(result.image_data, "QUJD")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "nano_banana_2")
        self.assertEqual(kwargs["json"]["metadata"]["aspectRatio"], "16:9")
        self.assertEqual(
            kwargs["json"]["metadata"]["urls"][0],
            "data:image/jpeg;base64,AAA",
        )

    @patch("app.services.nanobanana.xiaobanshou.requests.post")
    def test_generate_parses_live_queued_shape(self, mock_post):
        service = NanoBananaXiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"id":"task_l9p1L6ZzyJ6t5ZNx36wJS35uL3GjHDai","task_id":"task_l9p1L6ZzyJ6t5ZNx36wJS35uL3GjHDai",'
            '"object":"image","model":"nano_banana_2","status":"queued","progress":0,"created_at":1774004420}'
        )
        mock_response.json.return_value = {
            "id": "task_l9p1L6ZzyJ6t5ZNx36wJS35uL3GjHDai",
            "task_id": "task_l9p1L6ZzyJ6t5ZNx36wJS35uL3GjHDai",
            "object": "image",
            "model": "nano_banana_2",
            "status": "queued",
            "progress": 0,
            "created_at": 1774004420,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch.object(service, "_poll_task") as mock_poll:
            mock_poll.return_value = service._extract_result(
                {"images": [{"url": "data:image/png;base64,QUJD"}]}
            )
            result = service.generate(prompt="sunrise landscape", aspect_ratio="16:9")

        self.assertTrue(result.success)
        self.assertEqual(result.mime_type, "image/png")
        self.assertEqual(result.image_data, "QUJD")
        mock_poll.assert_called_once_with("task_l9p1L6ZzyJ6t5ZNx36wJS35uL3GjHDai")

    @patch("app.services.nanobanana.xiaobanshou.requests.post")
    def test_generate_extracts_real_unauthorized_error_shape(self, mock_post):
        service = NanoBananaXiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = (
            '{"error":{"code":"","message":"无效的令牌 '
            '(request id: 20260320105735193316496YmkvTnF2)","type":"new_api_error"}}'
        )
        mock_response.json.return_value = {
            "error": {
                "code": "",
                "message": "无效的令牌 (request id: 20260320105735193316496YmkvTnF2)",
                "type": "new_api_error",
            }
        }
        http_error = requests.exceptions.HTTPError("401 Client Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        result = service.generate(
            prompt="sunrise landscape",
            aspect_ratio="16:9",
        )

        self.assertFalse(result.success)
        self.assertIn("无效的令牌", result.error_message)

    @patch("app.services.nanobanana.xiaobanshou.requests.get")
    def test_extract_result_parses_live_completed_video_url_shape(self, mock_get):
        service = NanoBananaXiaobanshou("test-key")

        mock_image_response = MagicMock()
        mock_image_response.content = b"\x89PNG\r\n\x1a\nfake"
        mock_image_response.headers = {"Content-Type": "image/png"}
        mock_image_response.raise_for_status.return_value = None
        mock_get.return_value = mock_image_response

        result = service._extract_result(
            {
                "id": "task_l9p1L6ZzyJ6t5ZNx36wJS35uL3GjHDai",
                "status": "completed",
                "video_url": "https://videos-us3.ss2.life/example-image",
                "completed_at": 1774004480,
            }
        )

        self.assertTrue(result.success)
        self.assertEqual(result.mime_type, "image/png")
        self.assertTrue(result.image_data)


if __name__ == "__main__":
    unittest.main()
