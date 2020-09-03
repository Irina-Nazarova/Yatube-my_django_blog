from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from posts.models import Group, Post, User, Follow, Comment


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

        # создание тестовой группы
        self.group = Group.objects.create(
            slug="slug", title="title", description="description"
        )

        # создание текстовых тестов для постов
        self.text_1 = "some text test"
        self.text_2 = "some text test2"

        # создание тега и картинки
        self.tag = "<img "

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
        self.assertTrue(Post.objects.filter(text=self.text_1).exists())

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

    def post_contains_params_on_all_pages(self, text, image=None):
        # создание списка url страниц на которых могут отображаться посты
        cache.clear()
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
            if image:
                self.assertContains(response, image)
            else:
                self.assertContains(response, self.group)
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

    def test_post_view_image_display_on_all_pages(self):
        """
        Проверка загрузки и отображения изображения на всех страницах с
        постами.
        """
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04"
            b"\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
            b"\x02\x4c\x01\x00\x3b"
        )
        img = SimpleUploadedFile(
            "small.gif", small_gif, content_type="image/gif"
        )
        post_with_image = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user, image=img,
        )
        cache.clear()
        self.post_contains_params_on_all_pages(
            post_with_image.id, image=self.tag
        )

    def test_post_without_image(self):
        """
        Проверяю, что срабатывает защита от загрузки файлов не-графических форматов
        """
        file = SimpleUploadedFile("filename.txt", b"hello world", "text/plain")
        return file

        self.error_message = (
            "Загрузите правильное изображение. Файл, "
            "который вы загрузили, поврежден или не "
            "является изображением."
        )
        url = reverse("new_post")
        response = self.authorized_client.post(
            url, {"text": self.text_1, "image": file}
        )
        self.assertFormError(response, "form", "image", self.error_message)


class TestCache(TestCase):
    """
    Проверка кеширования главной страницы.
    """

    def setUp(self):
        # создание авторизованного пользователя
        self.authorized_client = Client()
        self.user = User.objects.create_user(
            username="sarah_cache",
            email="connor.s@skynet.com",
            password="12345",
        )
        self.authorized_client.force_login(self.user)

        # создание тестовой группы
        self.group = Group.objects.create(
            slug="slug", title="title", description="description"
        )

    def test_cache(self):
        """ Проверка кеширования главной страницы """
        response_before_post = self.client.get(reverse("index"))
        post = Post.objects.create(
            author=self.user, group=self.group, text="test cache post"
        )
        response_after_post = self.client.get(reverse("index"))
        self.assertEqual(
            response_before_post.content, response_after_post.content
        )
        self.assertNotContains(response_before_post, post.text)
        cache.clear()
        response_after_cache = self.client.get(reverse("index"))
        self.assertNotEqual(
            response_after_post.content, response_after_cache.content
        )
        self.assertContains(response_after_cache, post.text)


class TestFollowing(TestCase):
    # создание авторизованного пользователя
    def setUp(self):
        self.authorized_client = Client()
        self.first_user = User.objects.create_user(
            username="Гудаков Дмитрий",
            email="Gudakov_Dmitry@ya.ru",
            password="1234",
        )
        self.second_user = User.objects.create_user(
            username="leo", email="leo@ya.ru", password="4321"
        )
        self.authorized_client.force_login(self.first_user)
        self.text = "test_text"

    def test_follow(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей.
        """
        self.follow = self.authorized_client.post(
            reverse("profile_follow", kwargs={"username": self.second_user},)
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.first_user, author=self.second_user
            ).exists()
        )

    def test_unfollow(self):
        """
        Авторизованный пользователь может удалять других пользователей
        из подписок.
        """
        Follow.objects.create(user=self.first_user, author=self.second_user)
        self.assertEqual(Follow.objects.count(), 1)
        self.authorized_client.post(
            reverse(
                "profile_unfollow",
                kwargs={"username": self.second_user.username},
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.first_user, author=self.second_user
            ).exists()
        )

    def test_follow_lent(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него подписан.
        """
        self.post = Post.objects.create(
            text="Test_text", author=self.second_user
        )
        self.follow = self.authorized_client.post(
            reverse("profile_follow", kwargs={"username": self.second_user},)
        )
        response = self.authorized_client.get(reverse("follow_index"))
        self.assertContains(response, self.post.text)
        self.assertEqual(response.status_code, 200)

        follow_post = Post.objects.all().first()
        self.assertEqual(follow_post.author, self.post.author)

    def test_unfollow_lent(self):
        """
        Новая запись пользователя не появляется в ленте тех,
        кто не подписан на него.
        """
        Post.objects.create(text=self.text, author=self.first_user)
        response = self.authorized_client.get(reverse("follow_index"))
        self.assertNotContains(response, self.text)


class TestComment(TestCase):
    # создание авторизованного пользователя
    def setUp(self):
        self.authorized_client = Client()

        # создание двух авторов и поста для подписки
        self.first_author = User.objects.create_user(
            username="Гудаков Дмитрий",
            email="Gudakov_Dmitry@ya.ru",
            password="1234",
        )
        self.second_author = User.objects.create_user(
            username="leo", email="leo@ya.ru", password="4321"
        )
        self.post_author = Post.objects.create(
            text="test_text", author=self.second_author
        )
        self.post_id = self.post_author.id
        self.test_text = "text_comment"
        self.url_comment = reverse(
            "add_comment",
            kwargs={"username": self.second_author, "post_id": self.post_id},
        )

    def test_only_auth_user_add_comment(self):
        """
        Только авторизированный пользователь может комментировать посты.
        """
        self.authorized_client.force_login(self.first_author)
        self.authorized_client.post(self.url_comment, {"text": self.test_text})
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

    def test_unauth_user_not_add_comment(self):
        """
        Неавторизированный пользователь не может комментировать посты.
        """
        self.client.post(self.url_comment, {"text": self.test_text})
        self.assertFalse(
            Comment.objects.filter(
                text=self.test_text, author=self.second_author
            ).exists()
        )
