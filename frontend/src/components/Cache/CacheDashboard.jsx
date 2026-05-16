import React, { useState, useEffect } from 'react';

const CacheDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/cache/stats');
      if (!response.ok) throw new Error('Failed to fetch cache stats');
      const data = await response.json();
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInvalidate = async (model = null, engine = null) => {
    try {
      const payload = {};
      if (model) payload.model = model;
      if (engine) payload.engine = engine;

      const response = await fetch('/api/v1/cache/invalidate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Failed to invalidate cache');
      const data = await response.json();
      alert(data.message);
      fetchStats();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleCleanup = async () => {
    try {
      const response = await fetch('/api/v1/cache/cleanup', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to cleanup cache');
      const data = await response.json();
      alert(data.message);
      fetchStats();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-4">Loading cache stats...</div>;
  if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Semantic Cache Dashboard</h2>
      
      {/* Status */}
      <div className={`mb-4 p-3 rounded ${stats.enabled ? 'bg-green-100' : 'bg-gray-100'}`}>
        <span className="font-semibold">Status:</span> {stats.enabled ? 'Enabled' : 'Disabled'}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded">
          <div className="text-sm text-gray-600">Total Entries</div>
          <div className="text-2xl font-bold">{stats.total_entries}</div>
        </div>
        <div className="bg-green-50 p-4 rounded">
          <div className="text-sm text-gray-600">Total Hits</div>
          <div className="text-2xl font-bold">{stats.total_hits}</div>
        </div>
        <div className="bg-purple-50 p-4 rounded">
          <div className="text-sm text-gray-600">With Embeddings</div>
          <div className="text-2xl font-bold">{stats.entries_with_embeddings}</div>
        </div>
        <div className="bg-yellow-50 p-4 rounded">
          <div className="text-sm text-gray-600">Hit Rate</div>
          <div className="text-2xl font-bold">{(stats.hit_rate * 100).toFixed(1)}%</div>
        </div>
      </div>

      {/* Configuration */}
      <div className="mb-6 p-4 bg-gray-50 rounded">
        <h3 className="font-semibold mb-2">Configuration</h3>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div><span className="font-medium">Similarity Threshold:</span> {stats.similarity_threshold}</div>
          <div><span className="font-medium">TTL:</span> {stats.ttl_hours} hours</div>
        </div>
      </div>

      {/* Actions */}
      <div className="space-y-2">
        <h3 className="font-semibold">Actions</h3>
        <div className="flex gap-2">
          <button
            onClick={() => handleInvalidate()}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Invalidate All Cache
          </button>
          <button
            onClick={handleCleanup}
            className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
          >
            Cleanup Expired
          </button>
          <button
            onClick={fetchStats}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
};

export default CacheDashboard;
