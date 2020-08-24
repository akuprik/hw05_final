from time import sleep
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from .models import User, Post, Group

TEST_POST_TEXT = 'тестовое сообщение поста'
TEST_POST_EDIT_TEXT = 'новое сообщение тестового поста'


class TestPosts(TestCase):
    small_gif = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
        b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
        b'\x02\x4c\x01\x00\x3b'
    )

    def is_single_post(self,client, url, onlypost=False, post_text=TEST_POST_TEXT):
        response = client.get(url,follow=onlypost)
        if onlypost:
            post = response.context['post']
        else:
            self.assertEqual(len(response.context['page']), 1)
            post = response.context['page'][0]
        self.assertIsInstance(post, Post)
        self.assertEqual(post.text, post_text)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        return post

    def create_newpost_check_redirect_postcount(self, client, url_redirect, post_count_for_check):
        cache.clear()
        response = client.post(reverse('new'), {'group': self.group.pk, 'text': TEST_POST_TEXT, 'pk':0},
                                        follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], url_redirect)
        self.assertEqual(Post.objects.count(),post_count_for_check)
        return response

    def setUp(self):
        self.client = Client()    #не авторизованный клиент
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@tt.ru',
            password='1235678'
        )
        self.client_logined = Client()   #авторизованный (залогиненый) клиент
        self.client_logined.force_login(self.user)


        self.group = Group.objects.create(
            title='tstgroup',
            slug='tstgroup',
            description='description'
        )

    def test_profile(self):
        response = self.client.get(reverse('profile', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code,200)
        self.assertIsInstance(response.context["profile_user"], User)
        self.assertEqual(response.context["profile_user"].username, self.user.username)

    def test_public_post(self):
        response = self.create_newpost_check_redirect_postcount(self.client_logined,
                                                                url_redirect=reverse('index'),
                                                                post_count_for_check=1
                                                                )
        post = Post.objects.all()[0]
        self.assertEqual(post.group,self.group)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.text,TEST_POST_TEXT)

    def test_unauth_user_cant_publish_post(self):
        self.create_newpost_check_redirect_postcount(self.client,
                                                     url_redirect=f'{reverse("login")}?next={reverse("new")}',
                                                     post_count_for_check=0
                                                     )

    def test_post_in_sites(self):
        self.create_newpost_check_redirect_postcount(self.client_logined,
                                                     url_redirect=reverse('index'),
                                                     post_count_for_check=1
                                                     )
        self.is_single_post(self.client, reverse('index'))
        post = self.is_single_post(self.client, reverse('profile', kwargs={'username': self.user.username}))
        self.is_single_post(self.client,
                            reverse('post', kwargs={'username': self.user.username, 'post_id':post.pk}),
                            True
                            )

    def test_edit_post(self):
        post=Post.objects.create(
            text = TEST_POST_TEXT,
            group = self.group,
            author = self.user
        )
        response = self.client_logined.post(reverse('post_edit',
                                                    kwargs={'username': self.user.username, 'post_id':post.pk}
                                                    ),
                                            {'group': self.group.pk,
                                             'text': TEST_POST_EDIT_TEXT},
                                            follow=True
                                            )
        self.is_single_post(self.client_logined, reverse('index'),post_text=TEST_POST_EDIT_TEXT)
        self.is_single_post(self.client_logined,
                            reverse('profile', kwargs={'username': self.user.username}),
                            post_text=TEST_POST_EDIT_TEXT
                            )
        self.is_single_post(self.client_logined,
                            reverse('post', kwargs={'username': self.user.username, 'post_id':post.pk}),
                            onlypost=True,
                            post_text=TEST_POST_EDIT_TEXT
                            )
        self.is_single_post(self.client_logined,
                            reverse('group', kwargs={'slug':self.group.slug}),
                            post_text=TEST_POST_EDIT_TEXT
                            )

    def test_img_in_post(self):
        post=Post.objects.create(
            text = TEST_POST_TEXT,
            group = self.group,
            author = self.user,
        )
        img = SimpleUploadedFile(
            name='some.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        response = self.client_logined.post(reverse('post_edit',
                                                        kwargs={'username': self.user.username, 'post_id': post.pk}
                                                        ),
                                                {'group': self.group.pk,
                                                 'text': TEST_POST_EDIT_TEXT,
                                                 'image': img,
                                                 },
                                                follow=True
                                                )
        self.assertEqual(response.status_code,200)
        self.assertEqual(Post.objects.count(),1)
        self.assertContains(response,'<img')

    def test_img_in_profile_index_group(self):
        def check_image_for_url(client, url):
            cache.clear()
            response = client.get(url)
            self.assertContains(response, '<img', msg_prefix=f'for url = {url}' )

        img = SimpleUploadedFile(
            name='some.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        response = self.client_logined.post(reverse('new'), {'group':self.group.pk, 'text':TEST_POST_TEXT, 'image':img},
                                   follow=True)
        self.assertEqual(response.status_code,200)
        self.assertEqual(Post.objects.count(),1)
        check_image_for_url(self.client, reverse('index'))  #проверим на главной странице
        check_image_for_url(self.client, reverse('profile', kwargs={'username': self.user.username})) #в профайле
        check_image_for_url(self.client, reverse('group', kwargs={'slug':self.group.slug})) #в группе

    def test_img_no_graph(self):
        img = SimpleUploadedFile(
            name='some.txt',
            content=b'text in file',
            content_type='text/plain',
        )
        response = self.client_logined.post(reverse('new'),
                                                {'group': self.group.pk, 'text': TEST_POST_TEXT, 'image': img},
                                                follow=False)
        self.assertEqual(response.status_code,200) #остался на этой же странице
        self.assertEqual(Post.objects.count(),0) #новый пост в базу не добавился
        self.assertFormError(response,'form', 'image',
                             errors=['Загрузите правильное изображение. ' 
                                     'Файл, который вы загрузили, поврежден или не является изображением.']
                             )

    def test_cache(self):
        cache.clear()
        post=Post.objects.create(
            text = TEST_POST_TEXT,
            group = self.group,
            author = self.user,
        )
        self.client.get(reverse('index')) #закешируем страницу
        #отредактируем пост
        self.client_logined.post(reverse('post_edit',
                                                    kwargs={'username': self.user.username, 'post_id':post.pk}
                                                    ),
                                            {'group': self.group.pk,
                                             'text': TEST_POST_EDIT_TEXT},
                                            follow=True
                                            )
        response = self.client.get(reverse('index')) #вызовим страницу, должна быть из кеша
        self.assertContains(response, TEST_POST_TEXT) #текст поста не изменился
        sleep(21)
        response = self.client.get(reverse('index')) #вызовим страницу, должна обновиться
        self.assertContains(response, TEST_POST_EDIT_TEXT) #текст поста изменился






class CommonTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_404(self):
        response = self.client.get('test404')
        self.assertEqual(response.status_code,404)
