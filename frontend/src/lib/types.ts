// Common types used across the application
export interface SetupStatus {
  completed: boolean;
  steps_done: string[];
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}

export interface ApiError {
  message: string;
  code?: number;
  details?: any;
}
