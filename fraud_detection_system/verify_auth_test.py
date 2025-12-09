import unittest
from app import app, db, User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory DB for tests
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def register(self, username, password):
        return self.app.post('/register', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_access_denied_without_login(self):
        # Try to access protected route
        response = self.app.post('/analyze', json={'data': 'test'})
        # Should be 401 or redirect to login. Flask-Login standard is 401 for json/API calls usually if customized, 
        # but default login_required redirects to login_view.
        # Since /analyze is POST, the redirect might be 302.
        # Let's check status code.
        self.assertIn(response.status_code, [401, 302]) 

    def test_registration_and_login(self):
        # Register
        rv = self.register('testuser', 'password123')
        self.assertEqual(rv.status_code, 200)
        # Should be on login page now (redirected)
        self.assertIn(b'Login', rv.data)

        # Login
        rv = self.login('testuser', 'password123')
        self.assertEqual(rv.status_code, 200)
        # Should be on index page now
        self.assertIn(b'FraudGuard', rv.data)
        
        # Access Protected Route
        # We need mock engine output or handle the error gracefully. 
        # sending empty data returns 400.
        rv = self.app.post('/analyze', json={'data': ''}, follow_redirects=True)
        self.assertEqual(rv.status_code, 400) # 400 means it reached the function (auth passed)

        # Logout
        rv = self.logout()
        self.assertIn(b'Login', rv.data)
        
        # Access Protected Route again
        rv = self.app.post('/analyze', json={'data': 'test'})
        self.assertIn(rv.status_code, [401, 302])

if __name__ == '__main__':
    unittest.main()
