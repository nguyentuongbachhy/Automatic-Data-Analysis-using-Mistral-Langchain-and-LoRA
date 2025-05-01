import React, { createContext, useEffect, useReducer } from 'react';
import { getCurrentUser, loginUser, logoutUser, registerUser } from '../services/api';
import { AuthState, LoginCredentials, User } from '../types';
import { getWithExpiry, setWithExpiry } from '../utils/storage';

// Define AuthContextType interface that was missing
export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

// Constants for localStorage
const TOKEN_KEY = 'auth-token';
const USER_KEY = 'auth-user';
const TOKEN_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

// Initial State - match properties with AuthState interface
const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  token: localStorage.getItem(TOKEN_KEY),
  loading: true,
  error: null,
};

// Context
const AuthContext = createContext<AuthContextType>({
  ...initialState,
  login: async () => { },
  register: async () => { },
  logout: async () => { },
  refreshUser: async () => { },
});

// Reducer
type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'AUTH_FAILURE'; payload: string }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'AUTH_LOCAL'; payload: { user: User; token: string } }
  | { type: 'AUTH_REFRESH'; payload: User };

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'AUTH_START':
      return {
        ...state,
        loading: true,
        error: null,
      };
    case 'AUTH_SUCCESS':
      return {
        ...state,
        isAuthenticated: true,
        loading: false,
        user: action.payload.user,
        token: action.payload.token,
        error: null,
      };
    case 'AUTH_FAILURE':
      return {
        ...state,
        isAuthenticated: false,
        loading: false,
        user: null,
        token: null,
        error: action.payload,
      };
    case 'AUTH_LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        error: null,
      };
    case 'AUTH_LOCAL':
      return {
        ...state,
        isAuthenticated: true,
        loading: false,
        user: action.payload.user,
        token: action.payload.token,
        error: null,
      };
    case 'AUTH_REFRESH':
      return {
        ...state,
        user: action.payload,
        loading: false,
      };
    default:
      return state;
  }
};

// Provider
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Function to refresh user data
  const refreshUser = async (): Promise<void> => {
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token) {
        throw new Error('No token available');
      }

      const user = await getCurrentUser();
      setWithExpiry(USER_KEY, user, TOKEN_EXPIRY);
      dispatch({ type: 'AUTH_REFRESH', payload: user });
    } catch (error: any) {
      if (error?.response?.status === 401) {
        // If token is invalid, logout
        await logout();
      }
      console.error('Failed to refresh user data:', error);
    }
  };

  // Load user on initial render
  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem(TOKEN_KEY);
      const userData = getWithExpiry(USER_KEY);

      if (!token) {
        dispatch({ type: 'AUTH_FAILURE', payload: 'No token found' });
        return;
      }

      // If we have cached user data, use it immediately
      if (userData) {
        dispatch({
          type: 'AUTH_LOCAL',
          payload: { user: userData, token }
        });

        // Still fetch latest user data in background
        refreshUser().catch(err =>
          console.error('Background refresh failed:', err)
        );
      } else {
        // No cached data, try to get user from API
        try {
          dispatch({ type: 'AUTH_START' });
          const user = await getCurrentUser();

          // Save user info in localStorage with expiry
          setWithExpiry(USER_KEY, user, TOKEN_EXPIRY);

          dispatch({
            type: 'AUTH_SUCCESS',
            payload: { user, token }
          });
        } catch (error: any) {
          const errorMessage = error?.response?.data?.error ||
            error.message ||
            'Authentication failed';

          // Clear stored data on auth failure
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);

          dispatch({ type: 'AUTH_FAILURE', payload: errorMessage });
        }
      }
    };

    loadUser();
  }, []);

  // Login function
  const login = async (email: string, password: string): Promise<void> => {
    try {
      dispatch({ type: 'AUTH_START' });

      // Match the LoginCredentials interface from auth.ts
      const credentials: LoginCredentials = { email, password };
      const { user, token } = await loginUser(credentials);

      // Save token to localStorage
      localStorage.setItem(TOKEN_KEY, token);

      // Save user info with expiry
      setWithExpiry(USER_KEY, user, TOKEN_EXPIRY);

      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user, token }
      });
    } catch (error: any) {
      // Improved error handling
      const errorMessage = error?.response?.data?.error ||
        error.message ||
        'Login failed';

      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage });
      throw new Error(errorMessage);
    }
  };

  // Register function
  const register = async (name: string, email: string, password: string): Promise<void> => {
    try {
      dispatch({ type: 'AUTH_START' });

      const { user, token } = await registerUser({ name, email, password });

      // Save token to localStorage
      localStorage.setItem(TOKEN_KEY, token);

      // Save user info with expiry
      setWithExpiry(USER_KEY, user, TOKEN_EXPIRY);

      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user, token }
      });
    } catch (error: any) {
      // Improved error handling
      const errorMessage = error?.response?.data?.error ||
        error.message ||
        'Registration failed';

      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage });
      throw new Error(errorMessage);
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      await logoutUser();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear storage
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);

      dispatch({ type: 'AUTH_LOGOUT' });
    }
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Export a custom hook for easier context usage
export const useAuth = (): AuthContextType => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;