from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')


def recipe_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


def create_recipe(user, **params):
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/sample-recipe',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_recipes_retrieve_fails_auth_required(self):
        res = self.client.get(RECIPES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_recipe_retrieve_fails_auth_required(self):
        user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123'
        )
        recipe = create_recipe(user=user)
        res = self.client.get(recipe_url(recipe.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_recipes_retrive_success(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_retrive_limited_to_user(self):
        other_user = create_user(
            email='other@example.com',
            password='testpass123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.filter(user=self.user).order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_retrive_success(self):
        recipe = create_recipe(user=self.user)

        res = self.client.get(recipe_url(recipe.id))
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_retrive_limited_to_user(self):
        other_user = create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_user_recipe = create_recipe(user=other_user)

        res = self.client.get(recipe_url(other_user_recipe.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_recipe_create_success(self):
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 22,
            'price': Decimal('5.25'),
            'description': 'Sample description',
            'link': 'http://example.com/sample-recipe',
        }

        res = self.client.post(RECIPES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_recipe_partial_update_success(self):
        original_link = 'http://example.com/sample-recipe'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link=original_link
        )
        payload = {'title': 'New title'}

        res = self.client.patch(recipe_url(recipe.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_recipe_full_update_success(self):
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sample description',
            link='http://example.com/sample-recipe',
        )
        payload = {
            'title': 'New title',
            'time_minutes': 30,
            'price': Decimal('10.50'),
            'description': 'New description',
            'link': 'http://example.com/new-link'
        }

        res = self.client.put(recipe_url(recipe.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_recipe_update_user_returns_error(self):
        other_user = create_user(
            email='other@example.com',
            password='testpass123'
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': other_user.id, 'user_id': other_user.id}

        res = self.client.patch(recipe_url(recipe.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_recipe_delete_success(self):
        recipe = create_recipe(user=self.user)
        res = self.client.delete(recipe_url(recipe.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_delete_limited_to_user(self):
        other_user = create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_user_recipe = create_recipe(user=other_user)

        res = self.client.delete(recipe_url(other_user_recipe.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            Recipe.objects.filter(id=other_user_recipe.id).exists()
        )
