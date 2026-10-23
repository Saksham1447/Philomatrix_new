import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import {
  FolderOpen,
  FileText,
  Upload,
  Download,
  Trash2,
  Eye,
  CheckCircle,
  AlertCircle,
  Filter,
  Search,
  BookOpen,
  Calendar,
  User as UserIcon,
  HardDrive
} from 'lucide-react';

interface StudyMaterial {
  id: string;
  title: string;
  description?: string;
  topic?: string;
  file_name: string;
  file_size: number;
  file_type: string;
  is_published: boolean;
  download_count: number;
  created_at: string;
  class_id?: string;
  class_name?: string;
  division_id?: string;
  division_name?: string;
  subject_id: string;
  subject_name: string;
  subject_code: string;
  faculty_id: string;
  faculty_name: string;
}

export const StudyMaterialsPage: React.FC = () => {
  const { user, activeRole, token } = useAuth();
  const queryClient = useQueryClient();

  const [selectedSubject, setSelectedSubject] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Form states for upload
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [topic, setTopic] = useState('');
  const [divisionId, setDivisionId] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [isPublished, setIsPublished] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const isTeacherOrAdmin = ['FACULTY', 'PRINCIPAL', 'SUPER_ADMIN'].includes(activeRole || '');

  // 1. Fetch study materials
  const { data: materials = [], isLoading } = useQuery<StudyMaterial[]>({
    queryKey: ['study-materials', selectedSubject],
    queryFn: async () => {
      let url = '/api/v1/study-materials';
      if (selectedSubject !== 'ALL') {
        url += `?subject_id=${selectedSubject}`;
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load study materials');
      return res.json();
    },
    enabled: !!token
  });

  // 2. Fetch divisions and subjects for upload form (if faculty/admin)
  const { data: divisions = [] } = useQuery<{ id: string; name: string; class_id: string }[]>({
    queryKey: ['academics-divisions'],
    queryFn: async () => {
      const res = await fetch('/api/v1/academics/divisions', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: isTeacherOrAdmin && !!token
  });

  const { data: subjects = [] } = useQuery<{ id: string; name: string; code: string }[]>({
    queryKey: ['academics-subjects'],
    queryFn: async () => {
      const res = await fetch('/api/v1/academics/subjects', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: !!token
  });

  // 3. Handle file upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please select a file to upload.');
      return;
    }
    if (!title.trim()) {
      setUploadError('Please provide a title for the material.');
      return;
    }
    if (!subjectId) {
      setUploadError('Please select a subject.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', title.trim());
      formData.append('description', description.trim());
      formData.append('topic', topic.trim());
      formData.append('class_id', 'none'); // backend auto-resolves from division
      if (divisionId) formData.append('division_id', divisionId);
      formData.append('subject_id', subjectId);
      formData.append('is_published', String(isPublished));

      const res = await fetch('/api/v1/study-materials/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to upload study material');
      }

      setUploadSuccess('Study material uploaded and stored securely!');
      setTitle('');
      setDescription('');
      setTopic('');
      setSelectedFile(null);
      setIsUploadOpen(false);
      queryClient.invalidateQueries({ queryKey: ['study-materials'] });
    } catch (err: any) {
      setUploadError(err.message || 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  // 4. Handle secure file download
  const handleDownload = async (materialId: string, fileName: string) => {
    try {
      const res = await fetch(`/api/v1/study-materials/${materialId}/download`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Download failed. You may not have permission to view this file.');
        return;
      }
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      alert('Error initiating file download');
    }
  };

  // 5. Delete material
  const handleDelete = async (materialId: string) => {
    if (!window.confirm('Are you sure you want to delete this study material? This cannot be undone.')) {
      return;
    }
    try {
      const res = await fetch(`/api/v1/study-materials/${materialId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Delete failed');
        return;
      }
      queryClient.invalidateQueries({ queryKey: ['study-materials'] });
    } catch (err) {
      alert('Error deleting material');
    }
  };

  const filteredMaterials = materials.filter(m => {
    const matchesSearch =
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.topic && m.topic.toLowerCase().includes(searchQuery.toLowerCase())) ||
      m.subject_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-xl p-6 text-white border border-indigo-900/40 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Educational Repository
              </span>
              <span className="text-xs text-indigo-200/70">Junior College Science (Class 11 & 12)</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Study Materials & Lecture Notes</h1>
            <p className="text-sm text-slate-300 mt-1">
              Access and distribute syllabus notes, chapter summaries, theory guides, and formula sheets.
            </p>
          </div>

          {isTeacherOrAdmin && (
            <button
              onClick={() => setIsUploadOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 focus:ring-offset-slate-900 shrink-0"
            >
              <Upload className="w-4 h-4" />
              Upload Study Material
            </button>
          )}
        </div>
      </div>

      {uploadSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg p-4 flex items-center justify-between text-sm shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
          <button onClick={() => setUploadSuccess(null)} className="text-emerald-700 font-semibold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Filters and Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Subject Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <button
            onClick={() => setSelectedSubject('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              selectedSubject === 'ALL'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Subjects
          </button>
          {subjects.map(s => (
            <button
              key={s.id}
              onClick={() => setSelectedSubject(s.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedSubject === s.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {s.code}: {s.name}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search notes by title or topic..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Materials Grid / Table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
          <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm font-medium">Loading educational resources...</p>
        </div>
      ) : filteredMaterials.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-sm">
          <FolderOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No Study Materials Found</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1">
            {searchQuery
              ? `No resources match your search "${searchQuery}".`
              : 'There are currently no notes or reference materials uploaded for this selection.'}
          </p>
          {isTeacherOrAdmin && (
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-4 inline-flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-sm"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload First Note
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredMaterials.map(item => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden group"
            >
              <div className="p-5">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold tracking-wider uppercase bg-indigo-50 text-indigo-700 border border-indigo-100">
                    {item.subject_code}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {item.is_published ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        PUBLISHED
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        DRAFT
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                  {item.title}
                </h3>
                {item.topic && (
                  <p className="text-xs font-semibold text-indigo-600 mt-0.5">
                    Topic: {item.topic}
                  </p>
                )}
                {item.description && (
                  <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                    {item.description}
                  </p>
                )}

                <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px] text-slate-500">
                  <div className="flex items-center gap-1.5 truncate">
                    <UserIcon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">{item.faculty_name}</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    <BookOpen className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{item.division_name || 'All Sections'}</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    <HardDrive className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{formatFileSize(item.file_size)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-2">
                <button
                  onClick={() => handleDownload(item.id, item.file_name)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download File
                </button>

                {isTeacherOrAdmin && (
                  <button
                    onClick={() => handleDelete(item.id)}
                    title="Delete Material"
                    className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full p-6 shadow-2xl relative animate-in fade-in zoom-in duration-150">
            <h2 className="text-lg font-bold text-slate-900 mb-1">Upload Study Material</h2>
            <p className="text-xs text-slate-500 mb-4">
              Add curriculum resources for enrolled students. Supported formats: PDF, DOC, PPT, Images, TXT (Max 25MB).
            </p>

            {uploadError && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-800 text-xs p-3 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Material Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Chapter 4: Laws of Motion Theory & Numericals"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Subject *
                  </label>
                  <select
                    required
                    value={subjectId}
                    onChange={e => setSubjectId(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                  >
                    <option value="">Select Subject</option>
                    {subjects.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.code}: {s.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Target Division
                  </label>
                  <select
                    value={divisionId}
                    onChange={e => setDivisionId(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                  >
                    <option value="">All Divisions</option>
                    {divisions.map(d => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Topic / Chapter Unit (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Classical Mechanics / Unit 2"
                  value={topic}
                  onChange={e => setTopic(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Brief Overview / Instructions (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Notes for students regarding formulas, derivations, or homework..."
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Select Educational File (PDF, DOC, PPT, Images) *
                </label>
                <input
                  type="file"
                  required
                  accept=".pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.txt"
                  onChange={e => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="publish_chk"
                  checked={isPublished}
                  onChange={e => setIsPublished(e.target.checked)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded"
                />
                <label htmlFor="publish_chk" className="text-xs font-medium text-slate-700">
                  Publish immediately (students and guardians can download right away)
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading}
                  className="inline-flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-sm transition-all disabled:opacity-50"
                >
                  {isUploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload & Save
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
