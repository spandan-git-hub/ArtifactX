import { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { caseService } from '../../services/caseService';
import { Header } from '../layout';
import {
  ArrowLeft,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  FileText,
} from 'lucide-react';

const CaseForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    investigator: '',
    status: 'active',
  });

  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(isEdit);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Load case data if editing
  useEffect(() => {
    if (isEdit && id) {
      const loadCase = async () => {
        try {
          setFetchLoading(true);
          const data = await caseService.getCase(id);
          setFormData({
            name: data.name || '',
            description: data.description || '',
            investigator: data.investigator || '',
            status: data.status || 'active',
          });
        } catch (err) {
          setError(err.response?.data?.detail || err.message || 'Failed to load case');
        } finally {
          setFetchLoading(false);
        }
      };
      loadCase();
    }
  }, [id, isEdit]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (isEdit) {
        await caseService.updateCase(id, formData);
        setSuccess('Case updated successfully!');
        setTimeout(() => navigate(`/cases/${id}`), 1500);
      } else {
        const newCase = await caseService.createCase(formData);
        setSuccess('Case created successfully!');
        setTimeout(() => navigate(`/cases/${newCase.id}`), 1500);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  if (fetchLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header
        breadcrumbs={[
          { label: 'ArtifactX', path: '/' },
          { label: 'Cases', path: '/cases' },
          { label: isEdit ? 'Edit Case' : 'New Case' },
        ]}
      />

      <div className="p-6 animate-in max-w-2xl mx-auto">
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-accent-cyan/20 flex items-center justify-center">
              <FileText className="h-5 w-5 text-accent-cyan" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{isEdit ? 'Edit Case' : 'Create New Case'}</h1>
              <p className="text-sm text-forensic-500">
                {isEdit ? 'Update case information' : 'Set up a new forensic investigation'}
              </p>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-accent-rose/10 border border-accent-rose/30">
              <div className="flex items-center gap-3 text-accent-rose">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="mb-6 p-4 rounded-lg bg-accent-emerald/10 border border-accent-emerald/30">
              <div className="flex items-center gap-3 text-accent-emerald">
                <CheckCircle className="h-5 w-5 flex-shrink-0" />
                <span>{success}</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Case Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-forensic-300 mb-2">
                Case Name *
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                placeholder="e.g., Smith vs. Johnson Evidence Review"
                className="w-full px-4 py-2.5 rounded-lg border border-forensic-700 bg-forensic-800
                           text-forensic-100 placeholder-forensic-500
                           focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20"
              />
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-forensic-300 mb-2">
                Description
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows={4}
                placeholder="Provide a detailed description of the case scope and objectives..."
                className="w-full px-4 py-2.5 rounded-lg border border-forensic-700 bg-forensic-800
                           text-forensic-100 placeholder-forensic-500
                           focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20 resize-none"
              />
            </div>

            {/* Investigator */}
            <div>
              <label htmlFor="investigator" className="block text-sm font-medium text-forensic-300 mb-2">
                Lead Investigator
              </label>
              <input
                type="text"
                id="investigator"
                name="investigator"
                value={formData.investigator}
                onChange={handleChange}
                placeholder="e.g., John Smith, Digital Forensics LLC"
                className="w-full px-4 py-2.5 rounded-lg border border-forensic-700 bg-forensic-800
                           text-forensic-100 placeholder-forensic-500
                           focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20"
              />
            </div>

            {/* Status */}
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-forensic-300 mb-2">
                Case Status
              </label>
              <select
                id="status"
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full px-4 py-2.5 rounded-lg border border-forensic-700 bg-forensic-800
                           text-forensic-100 focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20"
              >
                <option value="active">Active - Investigation in progress</option>
                <option value="archived">Archived - On hold or pending review</option>
                <option value="closed">Closed - Investigation complete</option>
              </select>
            </div>

            {/* Form Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-forensic-700">
              <Link
                to={isEdit ? `/cases/${id}` : '/cases'}
                className="btn-ghost flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Cancel
              </Link>
              <button
                type="submit"
                disabled={loading || !formData.name.trim()}
                className="btn-primary flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    {isEdit ? 'Update Case' : 'Create Case'}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CaseForm;