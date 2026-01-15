# UI/UX Review: Profile Page
**Date:** 2026-01-14
**Page:** `/profile`
**Reviewer:** Claude Code (UI/UX Design Agent)

---

## Executive Summary

The profile page currently implements a basic profile editing interface with avatar upload, display name, location, and bio fields. However, it's **missing critical climbing-specific fields** that exist in the backend User model. The page shows only 3 of approximately 15+ available user profile fields, leaving the majority of the user's climbing profile inaccessible.

**Critical Issue:** The frontend profile page is severely incomplete compared to the backend data model, which includes:
- Risk tolerance preferences
- Preferred grade system
- Gender and partner gender preferences
- Weight and weight difference preferences (for belay safety)
- Profile visibility settings
- Discipline-specific climbing profiles (sport, trad, bouldering, etc.)
- Experience tags (skills, equipment, logistics, preferences)

---

## Current Implementation Analysis

### What's Currently Shown
**File:** `/Users/jonathanhicks/dev/send_buddy/frontend/app/profile/page.tsx`

The profile page currently displays:
1. Avatar upload (with validation)
2. Display name
3. Home location
4. Bio
5. Edit/View mode toggle
6. Email (read-only)

### What's Missing from Backend Model

Based on the User model (`/Users/jonathanhicks/dev/send_buddy/backend/users/models.py`), these fields are NOT exposed in the UI:

**Basic Preferences:**
- `risk_tolerance` (conservative/balanced/aggressive)
- `preferred_grade_system` (YDS/French/V-Scale)
- `profile_visible` (privacy control)

**Gender & Partner Matching:**
- `gender` (male/female/non-binary/prefer not to say)
- `preferred_partner_gender` (no preference/prefer male/prefer female/prefer non-binary/same gender)

**Weight & Belay Safety:**
- `weight_kg` (for belay safety matching)
- `preferred_weight_difference` (no preference/similar/moderate/close)

**Climbing Disciplines:**
- `DisciplineProfile` objects (sport, trad, bouldering, multipitch, gym)
  - Grade ranges (comfortable min/max, projecting)
  - Years of experience
  - Skills (can lead, can belay, can build anchors)
  - Discipline-specific notes

**Experience Tags:**
- `UserExperienceTag` (skills, equipment, logistics, preferences)

---

## Critical Issues (High Priority)

### 1. Missing Climbing Profile Fields
**Severity:** Critical
**Impact:** Users cannot set their climbing preferences, making the matching algorithm incomplete

**Problem:**
The profile page only shows 3 basic fields (name, location, bio) but the backend supports extensive climbing-specific data. This means:
- Users can't specify their climbing grades/abilities
- No way to set risk tolerance or grade system preferences
- Partner matching preferences (gender, weight) are inaccessible
- Discipline profiles (sport, trad, bouldering) can't be created/edited
- Experience tags can't be managed

**Recommended Fix:**
Redesign the profile page into a multi-section layout:

```typescript
// Suggested structure in /app/profile/page.tsx

<div className="max-w-4xl mx-auto px-4 py-8">
  <h1 className="text-3xl font-bold mb-8">My Profile</h1>

  {/* Section 1: Basic Info */}
  <Card className="mb-6">
    <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
    {/* Avatar, display name, location, bio */}
  </Card>

  {/* Section 2: Climbing Preferences */}
  <Card className="mb-6">
    <h2 className="text-xl font-semibold mb-4">Climbing Preferences</h2>
    {/* Risk tolerance, preferred grade system */}
  </Card>

  {/* Section 3: Partner Preferences */}
  <Card className="mb-6">
    <h2 className="text-xl font-semibold mb-4">Partner Preferences</h2>
    {/* Gender, partner gender preference, weight, weight difference */}
  </Card>

  {/* Section 4: Discipline Profiles */}
  <Card className="mb-6">
    <h2 className="text-xl font-semibold mb-4">Climbing Disciplines</h2>
    {/* List of discipline profiles with add/edit/delete */}
  </Card>

  {/* Section 5: Experience & Tags */}
  <Card className="mb-6">
    <h2 className="text-xl font-semibold mb-4">Skills & Experience</h2>
    {/* Tag management UI */}
  </Card>

  {/* Section 6: Privacy */}
  <Card className="mb-6">
    <h2 className="text-xl font-semibold mb-4">Privacy Settings</h2>
    {/* Profile visibility toggle */}
  </Card>
</div>
```

**Implementation Priority:** Immediate - this is core functionality

---

### 2. No Profile Visibility Control
**Severity:** Critical
**Impact:** Users cannot control their privacy settings

**Problem:**
The backend has a `profile_visible` boolean field, but there's no UI to toggle it. This is a privacy concern - users should be able to hide their profile if they want.

**Recommended Fix:**
Add a dedicated Privacy Settings section with a toggle:

```typescript
<Card className="mb-6">
  <h2 className="text-xl font-semibold mb-4">Privacy Settings</h2>
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <label htmlFor="profile-visibility" className="font-medium">
          Profile Visibility
        </label>
        <p className="text-sm text-gray-600">
          When visible, other climbers can see your profile and match with you
        </p>
      </div>
      <Toggle
        id="profile-visibility"
        checked={user?.profile_visible}
        onChange={handleVisibilityChange}
        aria-label="Toggle profile visibility"
      />
    </div>
  </div>
</Card>
```

**Files to Create/Update:**
- `/Users/jonathanhicks/dev/send_buddy/frontend/components/ui/Toggle.tsx` (new component)
- `/Users/jonathanhicks/dev/send_buddy/frontend/app/profile/page.tsx` (update)

---

### 3. Missing Discipline Profile Management
**Severity:** Critical
**Impact:** Users cannot define what types of climbing they do or their skill levels

**Problem:**
The DisciplineProfile model allows users to have multiple climbing profiles (sport, trad, bouldering, etc.), each with:
- Grade ranges (comfortable and projecting)
- Experience level
- Skills (lead, belay, anchor building)

There's no UI to create, view, edit, or delete these profiles.

**Recommended Fix:**
Create a discipline profile management section with:
1. List of existing discipline profiles (cards)
2. "Add Discipline" button
3. Modal/form for creating/editing disciplines
4. Delete functionality

```typescript
// Component suggestion: /components/profile/DisciplineProfileCard.tsx
export const DisciplineProfileCard = ({ profile, onEdit, onDelete }) => (
  <Card className="mb-4">
    <div className="flex justify-between items-start mb-3">
      <div>
        <h3 className="font-semibold text-lg">{profile.discipline}</h3>
        <p className="text-sm text-gray-600">
          {profile.years_experience} years experience
        </p>
      </div>
      <div className="flex gap-2">
        <Button size="sm" variant="ghost" onClick={onEdit}>
          Edit
        </Button>
        <Button size="sm" variant="danger" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </div>

    <div className="space-y-2 text-sm">
      <div>
        <span className="font-medium">Comfortable Range:</span>{' '}
        {profile.comfortable_grade_min_display} - {profile.comfortable_grade_max_display}
      </div>
      {profile.projecting_grade_display && (
        <div>
          <span className="font-medium">Projecting:</span>{' '}
          {profile.projecting_grade_display}
        </div>
      )}
      <div className="flex gap-3 mt-2">
        {profile.can_lead && (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
            Can Lead
          </span>
        )}
        {profile.can_belay && (
          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
            Can Belay
          </span>
        )}
        {profile.can_build_anchors && (
          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
            Can Build Anchors
          </span>
        )}
      </div>
    </div>
  </Card>
);
```

**API Integration Needed:**
```typescript
// In /lib/api.ts
export const api = {
  // ... existing methods

  // Discipline profiles
  getDisciplineProfiles: async () => {
    const response = await fetch('/api/users/me/disciplines/', {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    return response.json();
  },

  createDisciplineProfile: async (data: DisciplineProfileData) => {
    const response = await fetch('/api/users/me/disciplines/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  updateDisciplineProfile: async (id: string, data: DisciplineProfileData) => {
    const response = await fetch(`/api/users/me/disciplines/${id}/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  deleteDisciplineProfile: async (id: string) => {
    await fetch(`/api/users/me/disciplines/${id}/`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` }
    });
  }
};
```

---

### 4. No Experience Tag Management
**Severity:** Critical
**Impact:** Users cannot indicate their skills, equipment, or preferences

**Problem:**
The backend has an ExperienceTag system with categories (skill, equipment, logistics, preference), but there's no UI to select/deselect tags.

**Recommended Fix:**
Create a tag selection interface grouped by category:

```typescript
// Component: /components/profile/ExperienceTagSelector.tsx
export const ExperienceTagSelector = ({
  selectedTags,
  onTagToggle
}: {
  selectedTags: string[];
  onTagToggle: (slug: string) => void;
}) => {
  const [allTags, setAllTags] = useState<ExperienceTag[]>([]);

  useEffect(() => {
    // Fetch all available tags from API
    api.getExperienceTags().then(setAllTags);
  }, []);

  const tagsByCategory = groupBy(allTags, 'category');

  return (
    <div className="space-y-6">
      {Object.entries(tagsByCategory).map(([category, tags]) => (
        <div key={category}>
          <h3 className="font-semibold text-sm text-gray-700 uppercase mb-3">
            {category}
          </h3>
          <div className="flex flex-wrap gap-2">
            {tags.map(tag => (
              <button
                key={tag.slug}
                onClick={() => onTagToggle(tag.slug)}
                className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                  selectedTags.includes(tag.slug)
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                aria-pressed={selectedTags.includes(tag.slug)}
              >
                {tag.display_name}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
```

---

### 5. Missing Form Components for New Fields
**Severity:** Critical
**Impact:** Cannot implement the missing fields without proper UI components

**Problem:**
The profile page will need several new form components:
- Select/dropdown for choices (risk tolerance, grade system, gender, etc.)
- Number input for weight
- Toggle switch for boolean fields
- Tag selector for experience tags
- Grade picker (specialized input for climbing grades)

**Recommended Fix:**
Create the following new UI components:

**A. Select Component**
```typescript
// File: /components/ui/Select.tsx
import React, { useId } from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: Array<{ value: string; label: string }>;
}

export const Select: React.FC<SelectProps> = ({
  label,
  error,
  options,
  className = '',
  id,
  required,
  ...props
}) => {
  const generatedId = useId();
  const selectId = id || generatedId;
  const errorId = `${selectId}-error`;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-600 ml-1" aria-label="required">*</span>}
        </label>
      )}
      <select
        id={selectId}
        required={required}
        aria-required={required}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? errorId : undefined}
        className={`w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
          error ? 'border-red-500' : 'border-gray-300'
        } ${className}`}
        {...props}
      >
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={errorId} className="mt-1 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};
```

**B. Toggle Component**
```typescript
// File: /components/ui/Toggle.tsx
import React from 'react';

interface ToggleProps {
  id?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  'aria-label'?: string;
}

export const Toggle: React.FC<ToggleProps> = ({
  id,
  checked,
  onChange,
  disabled = false,
  'aria-label': ariaLabel,
}) => {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
        checked ? 'bg-blue-600' : 'bg-gray-300'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
};
```

**C. NumberInput Component**
```typescript
// File: /components/ui/NumberInput.tsx
import React, { useId } from 'react';

interface NumberInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  unit?: string;
  helpText?: string;
}

export const NumberInput: React.FC<NumberInputProps> = ({
  label,
  error,
  unit,
  helpText,
  className = '',
  id,
  required,
  ...props
}) => {
  const generatedId = useId();
  const inputId = id || generatedId;
  const errorId = `${inputId}-error`;
  const helpId = `${inputId}-help`;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-600 ml-1" aria-label="required">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type="number"
          required={required}
          aria-required={required}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? errorId : (helpText ? helpId : undefined)}
          className={`w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            error ? 'border-red-500' : 'border-gray-300'
          } ${unit ? 'pr-12' : ''} ${className}`}
          {...props}
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">
            {unit}
          </span>
        )}
      </div>
      {helpText && !error && (
        <p id={helpId} className="mt-1 text-xs text-gray-500">
          {helpText}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};
```

---

### 6. No Character Count for Bio Field
**Severity:** Medium (moved from Critical)
**Impact:** Users don't know how much they can write

**Problem:**
The bio textarea has a `maxLength={1000}` but no visible character counter. This is poor UX - users should see how many characters they have left.

**Recommended Fix:**
Update the Textarea component to support character counting:

```typescript
// Update /components/ui/Textarea.tsx
export const Textarea: React.FC<TextareaProps & { showCount?: boolean }> = ({
  label,
  error,
  className = '',
  id,
  required,
  showCount = false,
  maxLength,
  value,
  ...props
}) => {
  const generatedId = useId();
  const textareaId = id || generatedId;
  const errorId = `${textareaId}-error`;
  const currentLength = (value as string)?.length || 0;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={textareaId} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-600 ml-1" aria-label="required">*</span>}
        </label>
      )}
      <textarea
        id={textareaId}
        required={required}
        maxLength={maxLength}
        value={value}
        aria-required={required}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? errorId : undefined}
        className={`w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
          error ? 'border-red-500' : 'border-gray-300'
        } ${className}`}
        {...props}
      />
      <div className="flex justify-between items-center mt-1">
        <div>
          {error && (
            <p id={errorId} className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}
        </div>
        {showCount && maxLength && (
          <p className="text-xs text-gray-500">
            {currentLength} / {maxLength}
          </p>
        )}
      </div>
    </div>
  );
};

// Then use it in profile page:
<Textarea
  label="Bio"
  value={formData.bio}
  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
  rows={4}
  maxLength={1000}
  showCount={true} // Enable character counter
/>
```

---

## Medium Priority Issues

### 7. Avatar Preview Missing
**Severity:** Medium
**Impact:** Users can't preview their new avatar before upload

**Problem:**
When a user selects a file, it immediately uploads. There's no preview or confirmation step.

**Recommended Fix:**
Add a preview state and confirm button:

```typescript
const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

const handleAvatarSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const validation = validateFile(file, {
    maxSize: 5 * 1024 * 1024,
    allowedTypes: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
  });

  if (!validation.valid) {
    setError(validation.error || 'Invalid file');
    return;
  }

  // Create preview
  const reader = new FileReader();
  reader.onloadend = () => {
    setAvatarPreview(reader.result as string);
  };
  reader.readAsDataURL(file);
  setAvatarFile(file);
};

const handleAvatarUpload = async () => {
  if (!avatarFile) return;
  // ... existing upload logic
  setAvatarPreview(null);
  setAvatarFile(null);
};

// In JSX:
{avatarPreview && (
  <div className="mt-4 p-4 border rounded-lg">
    <p className="text-sm font-medium mb-2">Preview:</p>
    <img
      src={avatarPreview}
      alt="Avatar preview"
      className="w-20 h-20 rounded-full object-cover"
    />
    <div className="flex gap-2 mt-2">
      <Button size="sm" onClick={handleAvatarUpload} isLoading={isLoading}>
        Upload
      </Button>
      <Button
        size="sm"
        variant="secondary"
        onClick={() => {
          setAvatarPreview(null);
          setAvatarFile(null);
        }}
      >
        Cancel
      </Button>
    </div>
  </div>
)}
```

---

### 8. Location Field Needs Geocoding
**Severity:** Medium
**Impact:** Users manually type location, but coordinates aren't set

**Problem:**
The backend has `home_lat` and `home_lng` fields for geographic matching, but the UI only accepts text input. The coordinates are never populated.

**Recommended Fix:**
Implement geocoding with a location autocomplete:

```typescript
// Option 1: Use Google Places Autocomplete
// Option 2: Use OpenStreetMap Nominatim (free)
// Option 3: Use Mapbox Geocoding

// Example with basic fetch to Nominatim:
const handleLocationChange = async (locationText: string) => {
  setFormData({ ...formData, home_location: locationText });

  // Debounced geocoding
  if (locationText.length > 3) {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(locationText)}`
      );
      const results = await response.json();
      if (results.length > 0) {
        // Store coordinates for backend
        setFormData(prev => ({
          ...prev,
          home_lat: results[0].lat,
          home_lng: results[0].lon
        }));
      }
    } catch (error) {
      console.error('Geocoding error:', error);
    }
  }
};
```

**Better UX:** Use a proper autocomplete component like:
- `react-google-autocomplete`
- `react-places-autocomplete`
- Custom implementation with dropdown

---

### 9. No Validation Feedback During Typing
**Severity:** Medium
**Impact:** Users only see errors after submission

**Problem:**
Form validation only happens on submit. Real-time validation would improve UX.

**Recommended Fix:**
Add live validation for:
- Display name (min 3 chars)
- Location (min length)
- Bio (character limit)
- Weight (if provided, must be 30-200 kg)

```typescript
const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

const validateField = (name: string, value: any) => {
  let error = '';

  switch (name) {
    case 'display_name':
      if (value.length < 3) {
        error = 'Display name must be at least 3 characters';
      } else if (value.length > 100) {
        error = 'Display name must be less than 100 characters';
      }
      break;
    case 'weight_kg':
      if (value && (value < 30 || value > 200)) {
        error = 'Weight must be between 30 and 200 kg';
      }
      break;
    // ... other fields
  }

  setFieldErrors(prev => ({ ...prev, [name]: error }));
  return error === '';
};

const handleFieldChange = (name: string, value: any) => {
  setFormData({ ...formData, [name]: value });
  validateField(name, value);
};
```

---

### 10. Missing Loading Skeleton for Initial Load
**Severity:** Medium
**Impact:** Blank screen while profile loads

**Problem:**
When the page first loads, there's no loading state - just empty content until the user data arrives from the auth store.

**Recommended Fix:**
Add a skeleton loader:

```typescript
// Component: /components/ui/Skeleton.tsx
export const Skeleton = ({ className = '' }: { className?: string }) => (
  <div
    className={`animate-pulse bg-gray-200 rounded ${className}`}
    aria-hidden="true"
  />
);

// In profile page:
if (!user) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Skeleton className="h-8 w-48 mb-8" /> {/* Title */}
      <Card>
        <div className="flex items-center space-x-4 mb-6">
          <Skeleton className="w-20 h-20 rounded-full" /> {/* Avatar */}
          <div className="flex-1">
            <Skeleton className="h-6 w-32 mb-2" /> {/* Name */}
            <Skeleton className="h-4 w-48" /> {/* Email */}
          </div>
        </div>
        <Skeleton className="h-4 w-24 mb-2" /> {/* Label */}
        <Skeleton className="h-10 w-full mb-4" /> {/* Input */}
        <Skeleton className="h-4 w-24 mb-2" /> {/* Label */}
        <Skeleton className="h-20 w-full" /> {/* Textarea */}
      </Card>
    </div>
  );
}
```

---

### 11. Success Message Auto-Dismiss
**Severity:** Medium
**Impact:** Success messages stay forever

**Problem:**
Success messages (`"Profile updated successfully"`, `"Avatar uploaded successfully"`) remain on screen indefinitely. They should auto-dismiss.

**Recommended Fix:**
```typescript
useEffect(() => {
  if (success) {
    const timer = setTimeout(() => {
      setSuccess('');
    }, 5000); // Dismiss after 5 seconds

    return () => clearTimeout(timer);
  }
}, [success]);
```

---

### 12. Edit Mode Doesn't Show All Editable Fields
**Severity:** Medium
**Impact:** Confusing which fields can be edited

**Problem:**
Email is shown in view mode but not in edit mode. Users might think they can change it (they can't). Also, avatar is always editable regardless of mode.

**Recommended Fix:**
Make it clear which fields are read-only:

```typescript
{/* Always show email as read-only with explanation */}
<div className="mb-4 p-3 bg-gray-50 rounded-lg">
  <label className="text-sm font-medium text-gray-600">Email (cannot be changed)</label>
  <p className="text-gray-900">{user?.email}</p>
</div>
```

---

## Polish Issues (Low Priority)

### 13. Avatar Placeholder Could Be More Distinctive
**Severity:** Low
**Impact:** Generic gray circle with initial

**Problem:**
The avatar placeholder just shows the first letter on a gray background. It works but isn't very engaging.

**Recommended Fix:**
Use a gradient based on the user's ID or name:

```typescript
const getAvatarGradient = (userId: string) => {
  const colors = [
    'from-blue-400 to-blue-600',
    'from-green-400 to-green-600',
    'from-purple-400 to-purple-600',
    'from-pink-400 to-pink-600',
    'from-yellow-400 to-orange-500',
  ];

  // Use userId to deterministically pick a color
  const index = parseInt(userId.slice(0, 8), 16) % colors.length;
  return colors[index];
};

// In JSX:
<div className={`w-20 h-20 rounded-full bg-gradient-to-br ${getAvatarGradient(user.id)} flex items-center justify-center overflow-hidden`}>
  {user?.avatar ? (
    <img src={user.avatar} alt="Avatar" className="w-full h-full object-cover" />
  ) : (
    <span className="text-2xl font-bold text-white">
      {user?.display_name?.charAt(0).toUpperCase()}
    </span>
  )}
</div>
```

---

### 14. No Cancel Confirmation in Edit Mode
**Severity:** Low
**Impact:** Accidental cancellation loses changes

**Problem:**
If a user has made changes and clicks "Cancel", they lose all unsaved work without warning.

**Recommended Fix:**
Track if form is dirty and show confirmation:

```typescript
const [isDirty, setIsDirty] = useState(false);

useEffect(() => {
  if (user && isEditing) {
    const hasChanges =
      formData.display_name !== user.display_name ||
      formData.home_location !== user.home_location ||
      formData.bio !== user.bio;
    setIsDirty(hasChanges);
  }
}, [formData, user, isEditing]);

const handleCancel = () => {
  if (isDirty) {
    if (window.confirm('You have unsaved changes. Are you sure you want to cancel?')) {
      setIsEditing(false);
      // Reset form to user data
      setFormData({
        display_name: user?.display_name || '',
        home_location: user?.home_location || '',
        bio: user?.bio || '',
      });
    }
  } else {
    setIsEditing(false);
  }
};
```

---

### 15. Improve Avatar Upload Affordance
**Severity:** Low
**Impact:** Hidden file input isn't obvious

**Problem:**
The "Change Avatar" link is small and easy to miss. Better visual design would encourage avatar uploads.

**Recommended Fix:**
Make it more prominent with hover effects:

```typescript
<label className="group cursor-pointer block">
  <div className="relative">
    <div className="w-20 h-20 rounded-full bg-gray-300 flex items-center justify-center overflow-hidden">
      {user?.avatar ? (
        <img src={user.avatar} alt="Avatar" className="w-full h-full object-cover" />
      ) : (
        <span className="text-2xl text-gray-600">
          {user?.display_name?.charAt(0).toUpperCase()}
        </span>
      )}
    </div>
    <div className="absolute inset-0 rounded-full bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all flex items-center justify-center">
      <span className="text-white text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
        Change
      </span>
    </div>
  </div>
  <input
    type="file"
    accept="image/jpeg,image/png,image/webp,image/gif"
    className="hidden"
    onChange={handleAvatarUpload}
    disabled={isLoading}
    aria-label="Upload avatar image"
  />
</label>
```

---

### 16. Add Keyboard Shortcuts
**Severity:** Low
**Impact:** Power users would appreciate keyboard nav

**Problem:**
No keyboard shortcuts for common actions (edit mode, save, cancel).

**Recommended Fix:**
```typescript
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    // Cmd/Ctrl + E to toggle edit mode
    if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
      e.preventDefault();
      setIsEditing(prev => !prev);
    }

    // Cmd/Ctrl + S to save (when in edit mode)
    if ((e.metaKey || e.ctrlKey) && e.key === 's' && isEditing) {
      e.preventDefault();
      // Trigger form submit
      document.getElementById('profile-form')?.dispatchEvent(
        new Event('submit', { bubbles: true, cancelable: true })
      );
    }

    // Escape to cancel edit mode
    if (e.key === 'Escape' && isEditing) {
      setIsEditing(false);
    }
  };

  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, [isEditing]);

// Add hint in UI
<p className="text-xs text-gray-500 mt-2">
  Tip: Press Cmd+E to edit, Cmd+S to save, Esc to cancel
</p>
```

---

### 17. No Breadcrumb or Back Navigation
**Severity:** Low
**Impact:** No clear way back to main app

**Problem:**
The profile page doesn't indicate where it sits in the app hierarchy or how to get back.

**Recommended Fix:**
Add breadcrumb or back button:

```typescript
<nav className="mb-6" aria-label="Breadcrumb">
  <ol className="flex items-center space-x-2 text-sm">
    <li>
      <a href="/" className="text-blue-600 hover:underline">
        Home
      </a>
    </li>
    <li className="text-gray-400">/</li>
    <li className="text-gray-700">Profile</li>
  </ol>
</nav>
```

---

## Accessibility Analysis

### Current State (Good)

The existing code has solid accessibility fundamentals:

**What's Working:**
- Input/Textarea components use proper `<label htmlFor>` associations
- Required fields marked with asterisk and `aria-label="required"`
- Error states use `aria-invalid` and `aria-describedby`
- Button component has `aria-busy` and `aria-live` for loading states
- Loading spinner has `aria-hidden="true"` and SR-only text
- Focus styles present (`:focus:outline-none :focus:ring-2`)

### Areas for Improvement

**A. Form Landmark Missing**
```typescript
// Current:
<form onSubmit={handleSubmit} className="space-y-4">

// Improved:
<form
  id="profile-form"
  onSubmit={handleSubmit}
  className="space-y-4"
  aria-label="Edit profile information"
>
```

**B. Success/Error Alert Roles**
The alerts already have visual distinction, but could be improved:

```typescript
// Current:
<div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4">{error}</div>

// Improved:
<div
  role="alert"
  aria-live="assertive"
  className="bg-red-50 text-red-600 p-3 rounded-lg mb-4"
>
  {error}
</div>

<div
  role="status"
  aria-live="polite"
  className="bg-green-50 text-green-600 p-3 rounded-lg mb-4"
>
  {success}
</div>
```

**C. Avatar File Input Needs Better Label**
```typescript
// Current:
<input
  type="file"
  accept="image/jpeg,image/png,image/webp,image/gif"
  className="hidden"
  onChange={handleAvatarUpload}
  disabled={isLoading}
/>

// Improved:
<input
  type="file"
  accept="image/jpeg,image/png,image/webp,image/gif"
  className="hidden"
  onChange={handleAvatarUpload}
  disabled={isLoading}
  aria-label="Upload profile picture (max 5MB, JPEG, PNG, WebP, or GIF)"
/>
```

**D. Page Title for Screen Readers**
```typescript
// Add at top of page:
<h1 className="text-3xl font-bold mb-8" id="page-title">
  My Profile
</h1>

// And in useEffect:
useEffect(() => {
  document.title = 'My Profile - Send Buddy';
}, []);
```

---

## Mobile Responsiveness

### Current State
The layout uses Tailwind's responsive utilities and should work reasonably well on mobile. The `max-w-3xl mx-auto px-4` provides good containment and padding.

### Potential Issues

**A. Avatar Size on Small Screens**
The 80px (w-20 h-20) avatar might be too large on very small screens.

```css
/* Consider responsive sizing: */
className="w-16 h-16 sm:w-20 sm:h-20 rounded-full"
```

**B. Button Layout in Edit Mode**
The save/cancel buttons are in a horizontal flex. On very narrow screens, they might be cramped.

```typescript
// Current:
<div className="flex space-x-2">

// Improved:
<div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
  <Button type="submit" isLoading={isLoading} className="w-full sm:w-auto">
    Save Changes
  </Button>
  <Button
    type="button"
    variant="secondary"
    onClick={() => setIsEditing(false)}
    disabled={isLoading}
    className="w-full sm:w-auto"
  >
    Cancel
  </Button>
</div>
```

**C. Test on Actual Devices**
The app should be tested on:
- iPhone SE (375px width - small)
- Standard phone (390-428px)
- Tablet (768px+)

---

## Design Consistency

### Issues

**A. Card Padding Consistency**
The Card component uses `p-6` globally. For the multi-section profile redesign, consider:
- Section headers might need different padding
- Nested cards (like discipline profiles) might need less padding

**B. Color Palette Consistency**
The app uses blue as primary (`blue-600`), gray for secondary, red for danger. This is good! But consider:
- Adding more semantic colors for climbing-specific features
- Success green (already used)
- Warning yellow/orange (for risk tolerance?)

**C. Typography Scale**
Current usage:
- Page title: `text-3xl font-bold`
- Card title: `text-xl font-semibold`
- Labels: `text-sm font-medium`

This is good hierarchy. Maintain it in the expanded profile.

---

## Performance Considerations

### Current Issues

**A. No Image Optimization**
Uploaded avatars aren't optimized. Consider:
- Client-side resize before upload (using canvas API or a library)
- Backend image processing (resize, compress)
- Serve WebP format with fallback

**B. No Caching Strategy**
User data is fetched on every page load. Consider:
- React Query / SWR for caching
- Optimistic updates for better perceived performance

**C. Large Form State**
When the profile expands to include all fields, the form state will be large. Consider:
- Splitting into multiple sub-forms/sections
- Only submitting changed fields (PATCH instead of full PUT)

---

## Recommendations Summary

### Immediate (Critical) - Do First

1. **Add all missing profile fields** - Implement climbing preferences, partner preferences, weight, privacy settings
2. **Create discipline profile management** - UI for adding/editing sport/trad/bouldering/etc profiles
3. **Implement experience tag selector** - Allow users to select skills/equipment tags
4. **Build required UI components** - Select, Toggle, NumberInput components
5. **Add profile visibility control** - Privacy toggle for hiding profile

**Estimated Effort:** 2-3 days of focused development

### Medium Priority - Next Sprint

6. Character counter for bio
7. Avatar preview before upload
8. Location geocoding/autocomplete
9. Live form validation
10. Loading skeleton state
11. Auto-dismiss success messages
12. Clarify read-only fields (email)

**Estimated Effort:** 1-2 days

### Polish - Future Enhancement

13. Gradient avatar placeholders
14. Cancel confirmation when form is dirty
15. Improve avatar upload visual design
16. Keyboard shortcuts
17. Breadcrumb navigation

**Estimated Effort:** 0.5-1 day

---

## Technical Implementation Guide

### Step-by-Step Implementation Plan

**Phase 1: Foundation (Day 1)**

1. Create new UI components:
   - `/components/ui/Select.tsx`
   - `/components/ui/Toggle.tsx`
   - `/components/ui/NumberInput.tsx`
   - `/components/ui/Skeleton.tsx`

2. Update existing components:
   - Add `showCount` prop to `/components/ui/Textarea.tsx`

3. Extend API client (`/lib/api.ts`):
   ```typescript
   // Add methods for:
   - getDisciplineProfiles()
   - createDisciplineProfile(data)
   - updateDisciplineProfile(id, data)
   - deleteDisciplineProfile(id)
   - getExperienceTags()
   - addExperienceTag(slug)
   - removeExperienceTag(slug)
   ```

**Phase 2: Profile Structure (Day 2)**

4. Create profile sub-components:
   - `/components/profile/BasicInfoSection.tsx`
   - `/components/profile/ClimbingPreferencesSection.tsx`
   - `/components/profile/PartnerPreferencesSection.tsx`
   - `/components/profile/DisciplineProfileCard.tsx`
   - `/components/profile/DisciplineProfileForm.tsx`
   - `/components/profile/ExperienceTagSelector.tsx`
   - `/components/profile/PrivacySection.tsx`

5. Refactor `/app/profile/page.tsx`:
   - Split into sections
   - Import and use new components
   - Update form state to include all fields

**Phase 3: Integration (Day 3)**

6. Wire up API calls:
   - Fetch discipline profiles on mount
   - Fetch experience tags on mount
   - Handle CRUD operations

7. Add validation:
   - Client-side validation for new fields
   - Error handling and display

8. Testing:
   - Manual testing of all fields
   - Accessibility testing
   - Mobile responsiveness testing

**Phase 4: Polish (Day 4 - Optional)**

9. Add medium priority features:
   - Character counter
   - Avatar preview
   - Loading states
   - Success message auto-dismiss

10. Add accessibility improvements:
    - Alert roles
    - Form landmarks
    - Keyboard shortcuts

---

## Code Examples for Key Features

### Complete Profile Page Structure (Suggested)

```typescript
// /app/profile/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Skeleton } from '@/components/ui/Skeleton';
import { BasicInfoSection } from '@/components/profile/BasicInfoSection';
import { ClimbingPreferencesSection } from '@/components/profile/ClimbingPreferencesSection';
import { PartnerPreferencesSection } from '@/components/profile/PartnerPreferencesSection';
import { DisciplineProfilesSection } from '@/components/profile/DisciplineProfilesSection';
import { ExperienceTagsSection } from '@/components/profile/ExperienceTagsSection';
import { PrivacySection } from '@/components/profile/PrivacySection';

export default function ProfilePage() {
  const { user, updateUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    document.title = 'My Profile - Send Buddy';
  }, []);

  if (!user) {
    return (
      <ProtectedRoute>
        <ProfileSkeleton />
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8" id="page-title">
          My Profile
        </h1>

        <BasicInfoSection user={user} onUpdate={updateUser} />
        <ClimbingPreferencesSection user={user} onUpdate={updateUser} />
        <PartnerPreferencesSection user={user} onUpdate={updateUser} />
        <DisciplineProfilesSection userId={user.id} />
        <ExperienceTagsSection userId={user.id} />
        <PrivacySection user={user} onUpdate={updateUser} />
      </div>
    </ProtectedRoute>
  );
}

function ProfileSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Skeleton className="h-8 w-48 mb-8" />
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="bg-white rounded-lg shadow-md p-6 mb-6">
          <Skeleton className="h-6 w-40 mb-4" />
          <Skeleton className="h-10 w-full mb-4" />
          <Skeleton className="h-10 w-full mb-4" />
          <Skeleton className="h-10 w-32" />
        </div>
      ))}
    </div>
  );
}
```

### Partner Preferences Section Example

```typescript
// /components/profile/PartnerPreferencesSection.tsx
'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { NumberInput } from '@/components/ui/NumberInput';
import { api } from '@/lib/api';

interface PartnerPreferencesSectionProps {
  user: User;
  onUpdate: (user: User) => void;
}

export const PartnerPreferencesSection = ({ user, onUpdate }: PartnerPreferencesSectionProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    gender: user.gender || '',
    preferred_partner_gender: user.preferred_partner_gender || 'no_preference',
    weight_kg: user.weight_kg || null,
    preferred_weight_difference: user.preferred_weight_difference || 'no_preference',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const updatedUser = await api.updateProfile(formData);
      onUpdate(updatedUser);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update preferences');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="mb-6">
      <h2 className="text-xl font-semibold mb-4">Partner Preferences</h2>

      {error && (
        <div role="alert" aria-live="assertive" className="bg-red-50 text-red-600 p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {!isEditing ? (
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-600">Gender</label>
            <p className="text-gray-900">
              {user.gender ? formatGender(user.gender) : 'Not specified'}
            </p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Preferred Partner Gender</label>
            <p className="text-gray-900">{formatPartnerGenderPreference(user.preferred_partner_gender)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Weight (for belay safety)</label>
            <p className="text-gray-900">
              {user.weight_kg ? `${user.weight_kg} kg (${Math.round(user.weight_kg * 2.20462)} lbs)` : 'Not specified'}
            </p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Acceptable Weight Difference</label>
            <p className="text-gray-900">{formatWeightDifferencePreference(user.preferred_weight_difference)}</p>
          </div>
          <Button onClick={() => setIsEditing(true)}>Edit Preferences</Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4" aria-label="Edit partner preferences">
          <Select
            label="Your Gender (Optional)"
            value={formData.gender}
            onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
            options={[
              { value: '', label: 'Prefer not to say' },
              { value: 'male', label: 'Male' },
              { value: 'female', label: 'Female' },
              { value: 'non_binary', label: 'Non-binary' },
              { value: 'prefer_not_to_say', label: 'Prefer not to say' },
            ]}
          />

          <Select
            label="Preferred Partner Gender"
            value={formData.preferred_partner_gender}
            onChange={(e) => setFormData({ ...formData, preferred_partner_gender: e.target.value })}
            options={[
              { value: 'no_preference', label: 'No preference' },
              { value: 'prefer_male', label: 'Prefer male' },
              { value: 'prefer_female', label: 'Prefer female' },
              { value: 'prefer_non_binary', label: 'Prefer non-binary' },
              { value: 'same_gender', label: 'Same gender as me' },
            ]}
          />

          <NumberInput
            label="Weight (Optional)"
            value={formData.weight_kg || ''}
            onChange={(e) => setFormData({
              ...formData,
              weight_kg: e.target.value ? parseInt(e.target.value) : null
            })}
            unit="kg"
            min={30}
            max={200}
            helpText="Used for safe belay partner matching. Weight must be between 30-200 kg."
          />

          <Select
            label="Acceptable Weight Difference"
            value={formData.preferred_weight_difference}
            onChange={(e) => setFormData({ ...formData, preferred_weight_difference: e.target.value })}
            options={[
              { value: 'no_preference', label: 'No preference' },
              { value: 'close', label: 'Close weight (± 10kg / 22lbs)' },
              { value: 'similar', label: 'Similar weight (± 15kg / 33lbs)' },
              { value: 'moderate', label: 'Moderate difference (± 30kg / 66lbs)' },
            ]}
          />

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
            <p className="font-medium mb-1">Why we ask about weight:</p>
            <p>
              Weight differences affect belay safety, especially for lead climbing.
              This helps match you with compatible partners for safer climbing sessions.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
            <Button type="submit" isLoading={isLoading} className="w-full sm:w-auto">
              Save Changes
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsEditing(false)}
              disabled={isLoading}
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
};

// Helper functions
function formatGender(gender: string): string {
  const map: Record<string, string> = {
    male: 'Male',
    female: 'Female',
    non_binary: 'Non-binary',
    prefer_not_to_say: 'Prefer not to say',
  };
  return map[gender] || gender;
}

function formatPartnerGenderPreference(pref: string): string {
  const map: Record<string, string> = {
    no_preference: 'No preference',
    prefer_male: 'Prefer male',
    prefer_female: 'Prefer female',
    prefer_non_binary: 'Prefer non-binary',
    same_gender: 'Same gender as me',
  };
  return map[pref] || pref;
}

function formatWeightDifferencePreference(pref: string): string {
  const map: Record<string, string> = {
    no_preference: 'No preference',
    close: 'Close weight (± 10kg / 22lbs)',
    similar: 'Similar weight (± 15kg / 33lbs)',
    moderate: 'Moderate difference (± 30kg / 66lbs)',
  };
  return map[pref] || pref;
}
```

---

## Files to Create/Modify

### New Files to Create

**UI Components:**
1. `/Users/jonathanhicks/dev/send_buddy/frontend/components/ui/Select.tsx`
2. `/Users/jonathanhicks/dev/send_buddy/frontend/components/ui/Toggle.tsx`
3. `/Users/jonathanhicks/dev/send_buddy/frontend/components/ui/NumberInput.tsx`
4. `/Users/jonathanhicks/dev/send_buddy/frontend/components/ui/Skeleton.tsx`

**Profile Components:**
5. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/BasicInfoSection.tsx`
6. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/ClimbingPreferencesSection.tsx`
7. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/PartnerPreferencesSection.tsx`
8. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/DisciplineProfileCard.tsx`
9. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/DisciplineProfileForm.tsx`
10. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/DisciplineProfilesSection.tsx`
11. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/ExperienceTagSelector.tsx`
12. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/ExperienceTagsSection.tsx`
13. `/Users/jonathanhicks/dev/send_buddy/frontend/components/profile/PrivacySection.tsx`

### Files to Modify

**Existing Files:**
1. `/Users/jonathanhicks/dev/send_buddy/frontend/app/profile/page.tsx` - Complete restructure
2. `/Users/jonathanhicks/dev/send_buddy/frontend/components/ui/Textarea.tsx` - Add character counter
3. `/Users/jonathanhicks/dev/send_buddy/frontend/lib/api.ts` - Add discipline/tag endpoints
4. `/Users/jonathanhicks/dev/send_buddy/frontend/lib/stores/authStore.ts` - May need to add discipline/tag state

---

## Conclusion

The profile page has a solid foundation with good accessibility practices, but it's **critically incomplete**. The backend supports a rich climbing profile with disciplines, grades, preferences, and tags, but the frontend only exposes 3 basic fields.

**Top 3 Priorities:**
1. Add all missing profile fields (preferences, partner matching, privacy)
2. Build discipline profile management UI
3. Implement experience tag selector

Once these core features are implemented, the profile page will be functional for the climbing buddy matching use case. The medium and low priority items will improve UX but aren't blockers.

**Estimated Total Effort:** 3-5 days for full implementation (critical + medium priority items).
