'use client';
import { useState } from 'react';
import { useAuth } from '../../../components/AuthProvider';
import { authHeaders } from '../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ProfilePage() {
  const { user, refetch } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [msg, setMsg] = useState('');
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '' });
  const [pwMsg, setPwMsg] = useState('');

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch(`${API}/api/auth/me`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ full_name: fullName }),
    });
    const data = await res.json();
    if (res.ok) { await refetch(); setMsg('Profile updated!'); }
    else setMsg(data.detail || 'Update failed');
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch(`${API}/api/auth/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(pwForm),
    });
    const data = await res.json();
    if (res.ok) { setPwForm({ current_password: '', new_password: '' }); setPwMsg('Password changed!'); }
    else setPwMsg(data.detail || 'Change failed');
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-8">Profile Settings</h1>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="font-semibold mb-4">Personal Info</h2>
          {msg && <div className="mb-3 text-sm text-green-300">{msg}</div>}
          <form onSubmit={saveProfile} className="space-y-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <p className="text-white">{user?.email}</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Full Name</label>
              <input value={fullName} onChange={e => setFullName(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
            </div>
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-semibold transition-colors">Save</button>
          </form>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="font-semibold mb-4">Change Password</h2>
          {pwMsg && <div className="mb-3 text-sm text-green-300">{pwMsg}</div>}
          <form onSubmit={changePassword} className="space-y-3">
            <input type="password" required placeholder="Current password" value={pwForm.current_password}
              onChange={e => setPwForm(f => ({...f, current_password: e.target.value}))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
            <input type="password" required placeholder="New password (min 8 chars)" minLength={8} value={pwForm.new_password}
              onChange={e => setPwForm(f => ({...f, new_password: e.target.value}))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-semibold transition-colors">Change Password</button>
          </form>
        </div>
      </div>
    </div>
  );
}
