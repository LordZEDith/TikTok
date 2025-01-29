import React, { useState } from 'react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const AuthModal = ({ isOpen, onClose }: AuthModalProps) => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    try {
      if (isLogin) {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        formData.append('grant_type', 'password');

        const response = await fetch('/api/auth/login', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const text = await response.text();
          let errorMessage;
          try {
            const data = JSON.parse(text);
            errorMessage = data.detail || 'Login failed';
          } catch {
            errorMessage = `Login failed: ${text || response.statusText}`;
          }
          setError(errorMessage);
          return;
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        onClose();
        window.location.reload();
      } else {
        const response = await fetch('/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            username,
            password,
          }),
        });

        if (!response.ok) {
          const text = await response.text();
          let errorMessage;
          try {
            const data = JSON.parse(text);
            errorMessage = data.detail || 'Registration failed';
          } catch {
            errorMessage = `Registration failed: ${text || response.statusText}`;
          }
          console.error('Registration error response:', text);
          setError(errorMessage);
          return;
        }

        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        formData.append('grant_type', 'password');

        const loginResponse = await fetch('/api/auth/login', {
          method: 'POST',
          body: formData,
        });

        if (!loginResponse.ok) {
          const text = await loginResponse.text();
          let errorMessage;
          try {
            const data = JSON.parse(text);
            errorMessage = data.detail || 'Login after registration failed';
          } catch {
            errorMessage = `Login after registration failed: ${text || loginResponse.statusText}`;
          }
          setError(errorMessage);
          return;
        }

        const loginData = await loginResponse.json();
        localStorage.setItem('token', loginData.access_token);
        localStorage.setItem('refresh_token', loginData.refresh_token);
        onClose();
        window.location.reload();
      }
    } catch (error) {
      console.error('Auth error:', error);
      setError('Failed to connect to server. Please try again.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50">
      <div className="bg-gray-900 p-8 rounded-lg w-96">
        <h2 className="text-2xl font-bold text-white mb-6">
          {isLogin ? 'Login to Continue' : 'Create an Account'}
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500 rounded text-red-500 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-gray-300 mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full p-2 rounded bg-gray-800 text-white border border-gray-700 focus:border-[#FE2C55] focus:outline-none"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-gray-300 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-2 rounded bg-gray-800 text-white border border-gray-700 focus:border-[#FE2C55] focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-gray-300 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2 rounded bg-gray-800 text-white border border-gray-700 focus:border-[#FE2C55] focus:outline-none"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-[#FE2C55] text-white rounded-md py-3 font-medium hover:bg-[#ef233c]"
          >
            {isLogin ? 'Login' : 'Sign Up'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
            className="text-gray-400 hover:text-white"
          >
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Login'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthModal; 