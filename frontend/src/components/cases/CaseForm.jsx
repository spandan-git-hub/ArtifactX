import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { caseService } from '../../services/caseService';

const CaseForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    investigator: '',
    status: 'active'
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Load case data if editing
  const loadCase = async () => {
    if (!isEdit) return;
    try {
      setLoading(true);
      const data = await caseService.getCase(id);
      setFormData(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load case');
    } finally {
      setLoading(false);
    }
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
      } else {
        const newCase = await caseService.createCase(formData);
        setSuccess('Case created successfully!');
        // Reset form after creation
        setFormData({
          name: '',
          description: '',
          investigator: '',
          status: 'active'
        });
        // Redirect to list after a short delay
        setTimeout(() => {
          navigate('/cases');
        }, 1500);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  // Load case on mount if editing
  // Note: useEffect not allowed in conditional, but we can call directly
  // We'll use a useEffect hook instead.
};

import { useEffect } from 'react';

const CaseFormWithEffect = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    investigator: '',
    status: 'active'
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (isEdit) {
      const loadCase = async () => {
        try {
          setLoading(true);
          const data = await caseService.getCase(id);
          setFormData(data);
        } catch (err) {
          setError(err.response?.data?.detail || err.message || 'Failed to load case');
        } finally {
          setLoading(false);
        }
      };
      loadCase();
    }
  }, [id, isEdit]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (isEdit) {
        await caseService.updateCase(id, formData);
        setSuccess('Case updated successfully!');
      } else {
        const newCase = await caseService.createCase(formData);
        setSuccess('Case created successfully!');
        // Reset form after creation
        setFormData({
          name: '',
          description: '',
          investigator: '',
          status: 'active'
        });
        // Redirect to list after a short delay
        setTimeout(() => {
          navigate('/cases');
        }, 1500);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6">{isEdit ? 'Edit Case' : 'Create New Case'}</h1>
      {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-600 rounded">{error}</div>}
      {success && <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-600 rounded">{success}</div>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Case Name *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Investigator</label>
          <input
            type="text"
            value={formData.investigator}
            onChange={(e) => setFormData({ ...formData, investigator: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Status</label>
          <select
            value={formData.status}
            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div className="flex items-center justify-end space-x-3">
          <button
            type="button"
            onClick={() => navigate('/cases')}
            className="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className={`px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 ${loading ? 'opacity-70' : ''}`}
          >
            {loading ? 'Saving...' : isEdit ? 'Update Case' : 'Create Case'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CaseFormWithEffect;