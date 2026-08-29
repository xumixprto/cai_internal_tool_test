from django.test import TestCase
from django.urls import resolve, reverse

from apps.demo_two.services.data import DemoTwoDataService


class DemoTwoTests(TestCase):
    def test_index_returns_200(self):
        response = self.client.get(reverse("demo_two:index"))
        self.assertEqual(response.status_code, 200)

    def test_service_returns_items(self):
        items = DemoTwoDataService.list_items()
        self.assertEqual(len(items), 3)
        self.assertIn("name", items[0])
        self.assertIn("type", items[0])
        self.assertIn("status", items[0])

    def test_url_namespace(self):
        self.assertEqual(reverse("demo_two:index"), "/apps/demo-two/")
        self.assertEqual(resolve("/apps/demo-two/").view_name, "demo_two:index")
