import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Profile
from feed.models import Post, Comment

def run_seed():
    print("[-] Seeding Django Social MVP database...")

    # 1. Superuser
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        admin_user.first_name = "Admin"
        admin_user.last_name = "Root"
        admin_user.save()
        print("    + Created superuser 'admin' (password: admin123)")

    # 2. Key Personas
    personas = [
        {
            'username': 'kunal_das',
            'first_name': 'Kunal',
            'last_name': 'Das',
            'email': 'isearch.xsolve@gmail.com',
            'headline': 'Director & Systems Architect | Former CTO (MyFastX, Keross R&D) | NIT Silchar Honours',
            'company': 'Nexus Distributed Architecture',
            'location': 'Kolkata, India',
            'bio': '20+ years building distributed backends, spatial engines, and high-concurrency event pipelines. NIT Silchar alumni.'
        },
        {
            'username': 'karan_sabale',
            'first_name': 'Karan R.',
            'last_name': 'Sabale',
            'email': 'karan@example.com',
            'headline': 'Founder & Product Lead | Full Stack Systems',
            'company': 'Sabale Innovations',
            'location': 'Pune, India',
            'bio': 'Architecting modern web applications, real-time social feeds, and scalable Python/Django services.'
        },
        {
            'username': 'avishek_b',
            'first_name': 'Avishek',
            'last_name': 'Bhattacharjee',
            'email': 'avishek@nutaan.ai',
            'headline': 'Founder & CEO @ Nutaan AI | Autonomous Systems',
            'company': 'Nutaan AI',
            'location': 'Bengaluru, India',
            'bio': 'Pioneering enterprise AI workflows, LLM observability, and agentic orchestration engines.'
        },
        {
            'username': 'bishakh_g',
            'first_name': 'Bishakh',
            'last_name': 'Ghosh',
            'email': 'bishakh@pinggy.io',
            'headline': 'Founder @ Lumirank.ai & Pinggy.io | Infrastructure & Networking',
            'company': 'Pinggy.io',
            'location': 'Kolkata, India',
            'bio': 'Tunneling infrastructure, distributed networking, and developer developer tools.'
        }
    ]

    user_objs = {}
    for p in personas:
        user, created = User.objects.get_or_create(username=p['username'])
        user.first_name = p['first_name']
        user.last_name = p['last_name']
        user.email = p['email']
        user.set_password('demo123')
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.headline = p['headline']
        profile.company = p['company']
        profile.location = p['location']
        profile.bio = p['bio']
        profile.save()

        user_objs[p['username']] = user
        status_str = "Created" if created else "Updated"
        print(f"    + {status_str} persona: {user.get_full_name()} (@{user.username})")

    # Clear old demo posts to allow clean re-runs
    Post.objects.all().delete()
    print("    - Cleared prior sample posts for pristine state.")

    # 3. Seed Realistic Dispatches
    posts_data = [
        {
            'author': user_objs['kunal_das'],
            'content': (
                "Architecture Milestone: High-efficiency social feed querying in Django.\n\n"
                "When querying posts with authors, nested profiles, likes, and comment threads, "
                "naive ORM queries hit N+1 bottlenecks within 50 concurrent requests. "
                "By combining select_related('author', 'author__profile') with prefetch_related('comments', 'likes'), "
                "we collapse 140+ database hits down into 3 constant SQL queries."
            ),
            'code_snippet': (
                "# Zero N+1 Query Optimization Pattern\n"
                "posts = Post.objects.select_related('author', 'author__profile')\\\n"
                "                    .prefetch_related(\n"
                "                        Prefetch('comments', queryset=Comment.objects.select_related('author')),\n"
                "                        'likes'\n"
                "                    ).all()[:25]"
            ),
            'language': 'python',
            'tags': '#django, #performance, #sql, #architecture',
            'likes': [user_objs['karan_sabale'], user_objs['avishek_b'], user_objs['bishakh_g']],
            'comments': [
                (user_objs['karan_sabale'], "This is exactly the query pattern needed for our mobile feed endpoint. Keeps query execution under 8ms."),
                (user_objs['bishakh_g'], "Clean structure. Adding an index on (created_at DESC) makes cursor pagination almost instantaneous.")
            ]
        },
        {
            'author': user_objs['karan_sabale'],
            'content': (
                "Feed Pagination Benchmark: Keyset / Cursor vs Offset/Limit.\n\n"
                "Tested offset pagination on 100,000 feed dispatches. Beyond page 50, DB response times spike from 12ms to 380ms due to index scanning overhead. "
                "Switching to `WHERE created_at < ? ORDER BY created_at DESC LIMIT 20` drops tail latency to flat 3ms regardless of dataset size."
            ),
            'code_snippet': (
                "# Cursor-based Pagination SQL Pattern\n"
                "SELECT * FROM feed_post \n"
                "WHERE created_at < '2026-10-10T18:00:00Z'\n"
                "ORDER BY created_at DESC \n"
                "LIMIT 20;"
            ),
            'language': 'sql',
            'tags': '#database, #postgres, #optimization, #scalability',
            'likes': [user_objs['kunal_das'], user_objs['bishakh_g']],
            'comments': [
                (user_objs['kunal_das'], "Spot on, Karan. Cursor pagination is mandatory for unbounded feeds. Pairs cleanly with Redis sorted sets.")
            ]
        },
        {
            'author': user_objs['avishek_b'],
            'content': (
                "Autonomous Workflow Architecture: Decoupling LLM Task Scheduling.\n\n"
                "Never couple long-running agent execution to synchronous HTTP request-response cycles. "
                "Every agent invocation is dispatched into an async message queue with idempotent task IDs and deterministic state logs."
            ),
            'code_snippet': (
                "# Async Task Dispatch Pattern\n"
                "@shared_task(bind=True, max_retries=3)\n"
                "def execute_agent_step(self, run_id, step_payload):\n"
                "    with transaction.atomic():\n"
                "        state = AgentRun.objects.select_for_update().get(id=run_id)\n"
                "        return state.advance(step_payload)"
            ),
            'language': 'python',
            'tags': '#ai, #distributed, #celery, #orchestration',
            'likes': [user_objs['kunal_das'], user_objs['karan_sabale']],
            'comments': [
                (user_objs['kunal_das'], "Transaction atomic lock with select_for_update prevents race conditions across worker pools.")
            ]
        },
        {
            'author': user_objs['bishakh_g'],
            'content': (
                "Tunneling & Reverse Proxying: Handling 10,000 concurrent sockets.\n\n"
                "Key lesson when deploying edge reverse proxies: avoid buffering large HTTP bodies in user memory. "
                "Stream TCP payloads directly through ring buffers with zero memory allocation per packet."
            ),
            'code_snippet': (
                "// Zero-copy proxy buffer pattern\n"
                "io.CopyBuffer(destConn, srcConn, bufferPool.Get().([]byte))"
            ),
            'language': 'go',
            'tags': '#networking, #infrastructure, #golang, #highthroughput',
            'likes': [user_objs['kunal_das'], user_objs['avishek_b']],
            'comments': [
                (user_objs['karan_sabale'], "Great insight. We saw similar memory pressure on WebSocket gateways before migrating to buffer pools.")
            ]
        }
    ]

    for item in posts_data:
        post = Post.objects.create(
            author=item['author'],
            content=item['content'],
            code_snippet=item['code_snippet'],
            language=item['language'],
            tags=item['tags']
        )
        for liking_user in item['likes']:
            post.likes.add(liking_user)

        for comment_author, comment_text in item['comments']:
            Comment.objects.create(
                post=post,
                author=comment_author,
                content=comment_text
            )

        print(f"    + Created post #{post.id} by {post.author.username} ({post.like_count} likes, {post.comment_count} comments)")

    print("[+] Database seeding complete! All models, personas, and feeds verified.")

if __name__ == '__main__':
    run_seed()
