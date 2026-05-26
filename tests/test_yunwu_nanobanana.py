import unittest

from app.constants import SettingKeys
from app.services.media_generation import media_generation_registry
from app.services.nanobanana.yunwu import NanoBananaYunwu


class NanoBananaYunwuTests(unittest.TestCase):
    def setUp(self):
        self.service = NanoBananaYunwu("test-key")

    def test_collect_ref_images_supports_batch_and_legacy_inputs(self):
        result = self.service._collect_ref_images(
            {
                "ref_images": [{"base64": "AAA", "mime": "image/png"}],
                "ref_image": "BBB",
                "ref_mime_type": "image/jpeg",
            }
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["mime"], "image/png")
        self.assertEqual(result[1]["base64"], "BBB")
        self.assertEqual(result[1]["mime"], "image/jpeg")

    def test_normalize_queue_url_rewrites_fal_queue_domain(self):
        normalized = self.service._normalize_queue_url(
            "https://queue.fal.run/fal-ai/nano-banana/requests/abc/status"
        )
        self.assertEqual(
            normalized,
            "https://yunwu.ai/fal-ai/nano-banana/requests/abc/status",
        )

    def test_extract_image_url_supports_nested_images_payload(self):
        image_url = self.service._extract_image_url(
            {
                "images": [
                    {
                        "url": "https://example.com/result.png",
                    }
                ]
            }
        )
        self.assertEqual(image_url, "https://example.com/result.png")

    def test_extract_error_message_supports_multiple_shapes(self):
        self.assertEqual(
            self.service._extract_error_message({"error": {"message": "bad request"}}),
            "bad request",
        )
        self.assertEqual(
            self.service._extract_error_message({"message": "plain error"}),
            "plain error",
        )


class MediaGenerationRegistryTests(unittest.TestCase):
    def test_yunwu_generator_is_registered(self):
        generator = media_generation_registry.get_image_generator("nanobanana", "yunwu")
        self.assertIsNotNone(generator)
        self.assertEqual(generator.provider, "yunwu")
        self.assertEqual(generator.platform, "nanobanana")

    def test_resolve_image_generator_prefers_saved_video_product_default(self):
        settings = {
            SettingKeys.VIDEO_PRODUCT_IMAGE_PLATFORM: "nanobanana",
            SettingKeys.VIDEO_PRODUCT_IMAGE_PROVIDER: "yunwu",
            SettingKeys.YUNWU_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_image_generator(settings)

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "nanobanana")
        self.assertEqual(provider, "yunwu")

    def test_resolve_image_generator_falls_back_to_configured_provider_in_platform(self):
        settings = {
            SettingKeys.YUNWU_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_image_generator(
            settings,
            platform="nanobanana",
            provider="missing-provider",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "nanobanana")
        self.assertEqual(provider, "yunwu")

    def test_resolve_video_generator_falls_back_to_sora2_setting(self):
        settings = {
            SettingKeys.SORA2_MODEL: "xiaobanshou",
            SettingKeys.XIAOBANSHOU_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(settings)

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "sora2")
        self.assertEqual(provider, "xiaobanshou")

    def test_resolve_image_generator_uses_nanobanana_setting_when_platform_is_explicit(self):
        settings = {
            SettingKeys.NANOBANANA_MODEL: "yunwu",
            SettingKeys.YUNWU_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_image_generator(
            settings,
            platform="nanobanana",
            provider="",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "nanobanana")
        self.assertEqual(provider, "yunwu")

    def test_resolve_video_generator_uses_sora2_setting_when_platform_is_explicit(self):
        settings = {
            SettingKeys.SORA2_MODEL: "xiaobanshou",
            SettingKeys.XIAOBANSHOU_API_KEY: "test-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(
            settings,
            platform="sora2",
            provider="",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "sora2")
        self.assertEqual(provider, "xiaobanshou")

    def test_resolve_video_generator_prefers_global_sora2_setting_over_video_product_default(self):
        settings = {
            SettingKeys.SORA2_MODEL: "bandianwa",
            SettingKeys.BANDIANWA_API_KEY: "test-key",
            SettingKeys.VIDEO_PRODUCT_VIDEO_PLATFORM: "sora2",
            SettingKeys.VIDEO_PRODUCT_VIDEO_PROVIDER: "xiaobanshou",
            SettingKeys.XIAOBANSHOU_API_KEY: "legacy-key",
        }

        generator, platform, provider = media_generation_registry.resolve_video_generator(
            settings,
            platform="sora2",
            provider="",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(platform, "sora2")
        self.assertEqual(provider, "bandianwa")


if __name__ == "__main__":
    unittest.main()
