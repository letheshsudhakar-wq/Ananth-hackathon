import React, { useEffect, useState } from 'react';
import { Loader2, RotateCcw, Save, UserRound } from 'lucide-react';
import { getProfile, updateProfile } from '@/services/api';
import { useOrganization } from '@/context/OrganizationContext';
import type { ProfileResponse, OrgType } from '@/types';

type ProfileForm = Pick<
  ProfileResponse,
  'full_name' | 'email' | 'role' | 'organization' | 'phone'
>;

export function Profile() {
  const { setOrg } = useOrganization();
  const [form, setForm] = useState<ProfileForm>({
    full_name: '',
    email: '',
    role: '',
    organization: 'enterprise',
    phone: '',
  });
  const [original, setOriginal] = useState<ProfileForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    getProfile()
      .then((profile) => {
        if (cancelled) return;
        const next = {
          full_name: profile.full_name,
          email: profile.email,
          role: profile.role,
          organization: profile.organization,
          phone: profile.phone,
        };
        setForm(next);
        setOriginal(next);
      })
      .catch((err) => {
        if (!cancelled) setMessage({ type: 'error', text: err?.message || 'Could not load profile.' });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const setField = (field: keyof ProfileForm, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const validate = () => {
    if (form.full_name.trim().length < 2) return 'Full name must contain at least 2 characters.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return 'Enter a valid email address.';
    if (form.role.trim().length < 2) return 'Role must contain at least 2 characters.';
    return null;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage(null);
    const validationError = validate();
    if (validationError) {
      setMessage({ type: 'error', text: validationError });
      return;
    }

    setSaving(true);
    try {
      const saved = await updateProfile({
        ...form,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        role: form.role.trim(),
        phone: form.phone.trim(),
      });
      const next = {
        full_name: saved.full_name,
        email: saved.email,
        role: saved.role,
        organization: saved.organization,
        phone: saved.phone,
      };
      setForm(next);
      setOriginal(next);
      setOrg(saved.organization as OrgType);
      setMessage({ type: 'success', text: 'Profile changes saved.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.message || 'Could not save profile.' });
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    if (original) setForm({ ...original });
    setMessage(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <Loader2 className="w-5 h-5 animate-spin text-[rgb(var(--accent))]" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Profile</h1>
        <p className="text-sm text-[rgb(var(--text-muted))] mt-1">Manage your local Ananth user profile</p>
      </div>

      {message && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          message.type === 'success'
            ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
            : 'border-red-400/20 bg-red-400/10 text-red-300'
        }`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-5">
        <div className="flex items-center gap-3 pb-4 border-b border-[rgb(var(--border-subtle))]">
          <div className="w-12 h-12 rounded-full bg-[rgb(var(--accent))]/15 flex items-center justify-center">
            <UserRound className="w-6 h-6 text-[rgb(var(--accent-soft))]" />
          </div>
          <div>
            <h2 className="font-semibold">{form.full_name || 'Unnamed user'}</h2>
            <p className="text-xs text-[rgb(var(--text-muted))]">{form.role || 'No role set'}</p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <label className="text-xs text-[rgb(var(--text-muted))]">
            Full name
            <input className="input mt-1.5" value={form.full_name} onChange={(e) => setField('full_name', e.target.value)} required />
          </label>
          <label className="text-xs text-[rgb(var(--text-muted))]">
            Email
            <input type="email" className="input mt-1.5" value={form.email} onChange={(e) => setField('email', e.target.value)} required />
          </label>
          <label className="text-xs text-[rgb(var(--text-muted))]">
            Role
            <input className="input mt-1.5" value={form.role} onChange={(e) => setField('role', e.target.value)} required />
          </label>
          <label className="text-xs text-[rgb(var(--text-muted))]">
            Phone
            <input className="input mt-1.5" value={form.phone} onChange={(e) => setField('phone', e.target.value)} />
          </label>
          <label className="text-xs text-[rgb(var(--text-muted))] sm:col-span-2">
            Organization
            <select className="input mt-1.5" value={form.organization} onChange={(e) => setField('organization', e.target.value)}>
              <option value="bank">Bank</option>
              <option value="enterprise">Enterprise</option>
              <option value="government">Government</option>
            </select>
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={reset} disabled={saving} className="btn btn-outline">
            <RotateCcw className="w-4 h-4" /> Cancel
          </button>
          <button type="submit" disabled={saving} className="btn btn-primary">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save changes
          </button>
        </div>
      </form>
    </div>
  );
}
