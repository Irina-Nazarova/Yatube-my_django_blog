from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

from posts.models import Group, Post, User, Follow, Comment

from PIL import Image
import tempfile

TEST_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache",}
}


@override_settings(CACHES=TEST_CACHE)
class ProfileTest(TestCase):
    def setUp(self):
        # создание авторизованного пользователя
        self.authorized_client = Client()
        self.user = User.objects.create_user(
            username="sarah", email="connor.s@skynet.com", password="12345"
        )
        self.authorized_client.force_login(self.user)

        # создание неавторизованного пользователя
        self.unauthorized_client = Client()
        self.unauthorized_client.logout()

        # создание тестовой группы
        self.group = Group.objects.create(
            slug="slug", title="title", description="description"
        )

        # создание текстовых тестов для постов
        self.text_1 = "some text test"
        self.text_2 = "some text test2"

        # создание тега и картинки
        self.tag = "<img"
        self.image = self._create_image()
        self.notImg = self._create_file()

        self.error_message = (
            "Загрузите правильное изображение. Файл, "
            "который вы загрузили, поврежден или не "
            "является изображением."
        )

    def test_profile(self):
        """
        Проверка наличия персональной страницы пользователя после его
        регистрации.
        """
        response = self.authorized_client.get(
            reverse("profile", args=(self.user.username,))
        )
        self.assertEqual(response.status_code, 200)

    def test_new_post_auth(self):
        """
        Проверка возможности опубликовать пост для авторизованного
        пользователя.
        """
        response = self.authorized_client.post(
            reverse("new_post"),
            data={"text": self.text_1, "group": self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        post = Post.objects.all().first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.text, self.text_1)

    def test_new_post_not_auth(self):
        """
        Проверка невозможности опубликовать пост для неавторизованного
        пользователя и последующего редиректа пользователя на страницу входа.
        """

        response = self.unauthorized_client.post(
            reverse("new_post"),
            data={"text": self.text_1, "group": self.group.id},
            follow=True,
        )
        login_url = reverse("login")
        new_post_url = reverse("new_post")
        target_url = f"{login_url}?next={new_post_url}"

        self.assertRedirects(response, target_url)
        self.assertEqual(Post.objects.count(), 0)

    def post_contains_params_on_all_pages(self, text):
        # создание списка url страниц на которых могут отображаться посты
        urls = [
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse(
                "post", kwargs={"username": self.user.username, "post_id": 1}
            ),
            reverse("group_posts", kwargs={"slug": self.group.slug}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
            self.assertContains(response, text)

    def test_post_on_all_pages(self):
        """
        Проверка отображения опубликованного поста на главной странице сайта,
        на персональной странице пользователя, на отдельной странице поста и
        на странице группы.
        """
        self.authorized_client.post(
            reverse("new_post"),
            data={"text": self.text_1, "group": self.group.id},
            follow=True,
        )
        self.post_contains_params_on_all_pages(self.text_1)

    def test_post_edit_on_all_pages(self):
        post = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user,
        )
        self.authorized_client.post(
            reverse(
                "post_edit",
                kwargs={"username": post.author, "post_id": post.id},
            ),
            data={"text": self.text_2, "group": self.group.id},
            follow=True,
        )
        # проверяю, что текст поменялся на всех страницах, где есть пост
        self.post_contains_params_on_all_pages(self.text_2)

    def test_404(self):
        """
        Проверка кода 404 при переходе на несуществующую страницу.
        """
        response = self.unauthorized_client.get("/404/")
        self.assertEqual(response.status_code, 404)
        response = self.authorized_client.get("/404/")
        self.assertEqual(response.status_code, 404)

    def _create_image(self):
        # создание картинки
        with tempfile.NamedTemporaryFile(suffix=" .png", delete=False) as f:
            image = Image.new("RGB", (200, 200), "white")
            image.save(f, "PNG")
        return open(f.name, mode="rb")

    def test_post_view_image(self):
        """
        Проверка отображения картинки на странице конкретного поста.
        """
        post = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user
        )
        response = self.authorized_client.post(
            reverse(
                "post_edit",
                kwargs={"username": self.user.username, "post_id": post.id},
            ),
            {"text": self.text_1, "image": self.image},
            follow=True,
        )

        self.assertContains(response, self.tag)

    def test_post_with_image(self):
        """
        Проверяю, что на главной странице, на странице профайла и на странице
        группы пост с картинкой отображается корректно, с тегом <img>
        """
        post = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user
        )

        response = self.authorized_client.post(
            reverse(
                "post_edit",
                kwargs={"username": self.user.username, "post_id": post.id},
            ),
            {
                "text": self.text_1,
                "image": self.image,
                "group": self.group.id,
            },
            follow=True,
        )

        urls = [
            reverse("group_posts", kwargs={"slug": self.group.slug}),
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse(
                "post", kwargs={"username": self.user.username, "post_id": 1}
            ),
        ]
        for url in urls:
            with self.subTest(url=url):
                response_index = self.authorized_client.get(url)
                self.assertContains(response_index, self.tag)

    def _create_file(self):
        file = SimpleUploadedFile("filename.txt", b"hello world", "text/plain")
        return file

    def test_post_without_image(self):
        """
        Проверяю, что срабатывает защита от загрузки файлов не-графических форматов
        """
        post = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user
        )

        response = self.authorized_client.post(
            reverse(
                "post_edit",
                kwargs={"username": self.user.username, "post_id": post.id},
            ),
            {"text": {self.text_1}, "image": self.notImg},
            follow=True,
        )
        self.assertFormError(response, "form", "image", self.error_message)


class TestCache(TestCase):
    """
    Проверка кеширования главной страницы.
    """

    def setUp(self):
        self.key = make_template_fragment_key("index_page", [1])

    def test_cache(self):
        self.client.get(reverse("index"))
        self.assertTrue(cache.get(self.key))
        cache.clear()
        self.assertFalse(cache.get(self.key))


class TestFollowing(TestCase):
    # создание авторизованного пользователя
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.first_user = User.objects.create_user(
            username="leo", email="leo@ya.ru", password="1234"
        )
        self.second_user = User.objects.create_user(
            username="leo2", email="leo2@ya.ru", password="4321"
        )

    def test_follow(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей.
        """
        self.authorized_client.force_login(self.first_user)
        self.assertEqual(Follow.objects.count(), 0)
        self.authorized_client.post(
            reverse(
                "profile_follow",
                kwargs={"username": self.second_user.username},
            )
        )
        self.assertEqual(Follow.objects.count(), 1)

    def test_unfollow(self):
        """
        Авторизованный пользователь может удалять других пользователей
        из подписок.
        """
        # self.authorized_client.force_login(self.second_user)
        self.assertEqual(Follow.objects.count(), 0)
        self.client.post(
            reverse(
                "profile_follow",
                kwargs={"username": self.second_user.username},
            )
        )
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_lent(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него подписан.
        """
        self.post = Post.objects.create(
            text="Test_text", author=self.second_user
        )
        self.authorized_client.force_login(self.first_user)
        self.authorized_client.get(
            reverse(
                "profile_follow",
                kwargs={"username": self.second_user.username},
            )
        )
        response = self.authorized_client.get(reverse("follow_index"))
        self.assertContains(response, self.post.text)
        self.assertEqual(response.status_code, 200)
        follow_post = Post.objects.all().first()
        self.assertEqual(follow_post.author, self.post.author)

    def test_unfollow_lent(self):
        """
        Новая запись пользователя не появляется в ленте тех, кто не подписан
        на него.
        """
        self.post = Post.objects.create(
            text="Test_text", author=self.second_user
        )
        response = self.unauthorized_client.get(reverse("follow_index"))
        self.login_target = (
            reverse("login") + "?next=" + reverse("follow_index")
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_target)


class TestComment(TestCase):
    # создание авторизованного пользователя
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()

        # создание двух авторов и поста для подписки
        self.first_author = User.objects.create_user(
            username="leo", email="leo@ya.ru", password="1234"
        )
        self.second_author = User.objects.create_user(
            username="leo2", email="leo2@ya.ru", password="4321"
        )
        self.post_author2 = Post.objects.create(
            text="test_text", author=self.second_author
        )
        self.post_id = self.post_author2.id
        self.test_text = "text_comment"

    def test_only_auth_user_add_comment(self):
        """
        Только авторизированный пользователь может комментировать посты.
        """
        response = reverse(
            "add_comment",
            kwargs={"username": self.second_author, "post_id": self.post_id},
        )
        self.authorized_client.force_login(self.first_author)
        self.authorized_client.post(response, {"text": self.test_text})
        response = self.authorized_client.get(
            reverse(
                "post",
                kwargs={
                    "username": self.second_author.username,
                    "post_id": self.post_id,
                },
            )
        )
        self.assertEqual(
            1, Comment.objects.filter(text=self.test_text).count()
        )
        self.assertContains(response, self.test_text)

    def test_only_not_auth_user_add_comment(self):
        response = reverse(
            "add_comment",
            kwargs={"username": self.second_author, "post_id": self.post_id},
        )
        self.authorized_client.post(response, {"text": self.test_text})
        response = self.authorized_client.get(
            reverse(
                "post",
                kwargs={
                    "username": self.second_author.username,
                    "post_id": self.post_id,
                },
            )
        )
        self.assertEqual(
            0, Comment.objects.filter(text=self.test_text).count()
        )
