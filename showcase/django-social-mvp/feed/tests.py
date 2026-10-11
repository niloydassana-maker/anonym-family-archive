from django.test import TestCase, Client
from django.contrib.auth.models import User
from accounts.models import Profile
from feed.models import Post, Comment

class SocialFeedArchitectureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='test_kunal', password='password123', first_name='Kunal', last_name='Das')
        self.user2 = User.objects.create_user(username='test_karan', password='password123', first_name='Karan', last_name='Sabale')

    def test_profile_signal_creation(self):
        """Verify profile is automatically attached via post_save signal."""
        self.assertTrue(hasattr(self.user1, 'profile'))
        self.assertEqual(self.user1.profile.headline, 'Software Engineer')

    def test_post_creation_and_feed_view(self):
        """Verify feed dispatches can be created and queried."""
        post = Post.objects.create(
            author=self.user1,
            content="Testing zero N+1 database performance.",
            code_snippet="print('Hello cluster')",
            language="python",
            tags="#test, #architecture"
        )
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Testing zero N+1 database performance.")
        self.assertContains(response, "#test")

    def test_like_toggle_endpoint(self):
        """Verify asynchronous like toggle."""
        post = Post.objects.create(author=self.user1, content="Like testing dispatch.")
        self.client.login(username='test_karan', password='password123')
        
        response = self.client.post(f'/post/{post.id}/like/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['like_count'], 1)

        # Toggle off
        response = self.client.post(f'/post/{post.id}/like/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['liked'])
        self.assertEqual(data['like_count'], 0)

    def test_comment_thread(self):
        """Verify discussion node append."""
        post = Post.objects.create(author=self.user1, content="Comment discussion node test.")
        self.client.login(username='test_karan', password='password123')
        
        response = self.client.post(f'/post/{post.id}/comment/', {'content': 'Architecture looks clean.'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.comments.count(), 1)
        self.assertEqual(post.comments.first().content, 'Architecture looks clean.')

    def test_demo_switcher(self):
        """Verify 1-click persona switch route."""
        response = self.client.get(f'/accounts/switch/{self.user2.id}/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], self.user2)
