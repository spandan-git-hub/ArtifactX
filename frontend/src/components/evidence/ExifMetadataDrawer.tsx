import { useState, useEffect } from 'react';
import {
  X,
  Camera,
  MapPin,
  ExternalLink,
  Calendar,
  Layers,
  Search,
  Loader2,
  FileImage,
  Sliders,
} from 'lucide-react';
import { getExifMetadata, downloadEvidenceFile } from '../../services/evidenceService';

const ExifMetadataDrawer = ({ isOpen, onClose, evidenceId, fileId, fileName }) => {
  const [loading, setLoading] = useState(true);
  const [exifRecord, setExifRecord] = useState(null);
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [filterQuery, setFilterQuery] = useState('');

  useEffect(() => {
    if (!isOpen || !evidenceId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);
    setExifRecord(null);

    // Fetch EXIF data
    getExifMetadata(evidenceId, fileId)
      .then((data) => {
        if (!isMounted) return;
        const rec = data.exif_records?.[0]?.metadata || null;
        setExifRecord(rec);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load EXIF data:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to extract EXIF metadata');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    // Fetch image preview blob if fileId exists
    if (fileId) {
      downloadEvidenceFile(evidenceId, fileId)
        .then((blob) => {
          if (!isMounted) return;
          const url = URL.createObjectURL(blob);
          setPreviewUrl(url);
        })
        .catch((err) => {
          console.warn('Could not load image preview blob:', err);
        });
    }

    return () => {
      isMounted = false;
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
      }
    };
  }, [isOpen, evidenceId, fileId]);

  if (!isOpen) return null;

  const camera = exifRecord?.camera || {};
  const gps = exifRecord?.gps || {};
  const rawExif = exifRecord?.exif_data || {};

  const filteredExifKeys = Object.keys(rawExif).filter((key) =>
    key.toLowerCase().includes(filterQuery.toLowerCase()) ||
    String(rawExif[key]).toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in">
      <div className="w-full max-w-2xl bg-forensic-900 border-l border-forensic-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-4 border-b border-forensic-800 flex items-center justify-between bg-forensic-950/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent-cyan/15 flex items-center justify-center border border-accent-cyan/20">
              <Camera className="w-5 h-5 text-accent-cyan" />
            </div>
            <div>
              <h3 className="font-semibold text-forensic-100 truncate max-w-[320px]">
                {fileName || 'Image EXIF Inspector'}
              </h3>
              <p className="text-xs text-forensic-400 font-mono">
                {exifRecord?.width && exifRecord?.height
                  ? `${exifRecord.width} × ${exifRecord.height} px`
                  : 'Media Metadata'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-forensic-400 hover:text-forensic-100 hover:bg-forensic-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-accent-cyan" />
              <span className="ml-3 text-forensic-400 text-sm font-mono">Extracting EXIF data...</span>
            </div>
          ) : error ? (
            <div className="card border-accent-rose/30 bg-accent-rose/5 p-4 text-accent-rose text-sm">
              {error}
            </div>
          ) : (
            <>
              {/* Image Preview Container */}
              {previewUrl && (
                <div className="card p-2 bg-forensic-950 flex items-center justify-center border-forensic-800 overflow-hidden max-h-[260px]">
                  <img
                    src={previewUrl}
                    alt={fileName || 'Evidence Image'}
                    className="max-h-[240px] w-auto object-contain rounded"
                  />
                </div>
              )}

              {/* Camera & Acquisition Details */}
              <div className="card bg-forensic-950/60 border-forensic-800 space-y-3">
                <div className="flex items-center gap-2 text-accent-cyan text-sm font-semibold border-b border-forensic-800/80 pb-2">
                  <Sliders className="w-4 h-4" />
                  <span>Camera & Hardware Metadata</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                    <span className="text-forensic-500 block mb-0.5">Make</span>
                    <span className="text-forensic-100 font-mono font-medium">{camera.make || '—'}</span>
                  </div>
                  <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                    <span className="text-forensic-500 block mb-0.5">Model</span>
                    <span className="text-forensic-100 font-mono font-medium">{camera.model || '—'}</span>
                  </div>
                  <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                    <span className="text-forensic-500 block mb-0.5">Software</span>
                    <span className="text-forensic-100 font-mono font-medium truncate block">{camera.software || '—'}</span>
                  </div>
                  <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                    <span className="text-forensic-500 block mb-0.5">ISO Speed</span>
                    <span className="text-accent-cyan font-mono font-medium">{camera.iso || '—'}</span>
                  </div>
                  <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                    <span className="text-forensic-500 block mb-0.5">F-Stop</span>
                    <span className="text-forensic-100 font-mono font-medium">{camera.f_number ? `f/${camera.f_number}` : '—'}</span>
                  </div>
                  <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                    <span className="text-forensic-500 block mb-0.5">Exposure Time</span>
                    <span className="text-forensic-100 font-mono font-medium">{camera.exposure_time || '—'}</span>
                  </div>
                </div>

                {camera.date_time && (
                  <div className="flex items-center gap-2 text-xs text-forensic-400 bg-forensic-900/50 p-2 rounded border border-forensic-800">
                    <Calendar className="w-3.5 h-3.5 text-accent-cyan" />
                    <span>Capture Timestamp:</span>
                    <span className="font-mono text-forensic-100">{camera.date_time}</span>
                  </div>
                )}
              </div>

              {/* GPS Geolocation Inspector */}
              <div className="card bg-forensic-950/60 border-forensic-800 space-y-3">
                <div className="flex items-center justify-between border-b border-forensic-800/80 pb-2">
                  <div className="flex items-center gap-2 text-accent-emerald text-sm font-semibold">
                    <MapPin className="w-4 h-4" />
                    <span>GPS Coordinates & Map Location</span>
                  </div>
                  {gps.has_gps ? (
                    <span className="badge badge-emerald text-[11px]">GPS Tags Found</span>
                  ) : (
                    <span className="badge badge-gray text-[11px]">No GPS Metadata</span>
                  )}
                </div>

                {gps.has_gps ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                      <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                        <span className="text-forensic-500 block mb-0.5">Latitude</span>
                        <span className="text-accent-emerald font-mono font-bold">{gps.latitude}°</span>
                      </div>
                      <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                        <span className="text-forensic-500 block mb-0.5">Longitude</span>
                        <span className="text-accent-emerald font-mono font-bold">{gps.longitude}°</span>
                      </div>
                      <div className="bg-forensic-900/80 p-2.5 rounded border border-forensic-800">
                        <span className="text-forensic-500 block mb-0.5">Altitude</span>
                        <span className="text-forensic-200 font-mono">{gps.altitude ? `${gps.altitude} m` : 'N/A'}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 pt-1">
                      {gps.map_url && (
                        <a
                          href={gps.map_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-primary py-1.5 px-3 text-xs inline-flex items-center gap-1.5"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          View on Google Maps
                        </a>
                      )}
                      {gps.osm_url && (
                        <a
                          href={gps.osm_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-secondary py-1.5 px-3 text-xs inline-flex items-center gap-1.5"
                        >
                          <MapPin className="w-3.5 h-3.5 text-accent-emerald" />
                          OpenStreetMap
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-forensic-500 py-1">
                    This file does not contain embedded GPS location metadata tags.
                  </p>
                )}
              </div>

              {/* Raw EXIF Key-Value Inspector */}
              <div className="card bg-forensic-950/60 border-forensic-800 space-y-3">
                <div className="flex items-center justify-between border-b border-forensic-800/80 pb-2">
                  <div className="flex items-center gap-2 text-forensic-200 text-sm font-semibold">
                    <Layers className="w-4 h-4 text-accent-violet" />
                    <span>Raw EXIF Key-Value Dictionary</span>
                  </div>
                  <span className="text-xs text-forensic-500 font-mono">
                    {Object.keys(rawExif).length} Tags
                  </span>
                </div>

                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-forensic-500" />
                  <input
                    type="text"
                    value={filterQuery}
                    onChange={(e) => setFilterQuery(e.target.value)}
                    placeholder="Search EXIF tag name or value..."
                    className="input pl-8 py-1.5 text-xs w-full bg-forensic-900"
                  />
                </div>

                <div className="max-h-60 overflow-y-auto rounded border border-forensic-800 bg-forensic-900/90 text-xs">
                  {filteredExifKeys.length === 0 ? (
                    <p className="p-3 text-forensic-500 text-center">No EXIF tags found matching query.</p>
                  ) : (
                    <table className="w-full text-left font-mono">
                      <thead className="bg-forensic-950 sticky top-0 text-forensic-400 border-b border-forensic-800">
                        <tr>
                          <th className="py-2 px-3">Tag Name</th>
                          <th className="py-2 px-3">Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-forensic-800/60">
                        {filteredExifKeys.map((key) => (
                          <tr key={key} className="hover:bg-forensic-800/40">
                            <td className="py-1.5 px-3 text-accent-cyan font-medium truncate max-w-[160px]">
                              {key}
                            </td>
                            <td className="py-1.5 px-3 text-forensic-200 break-all">
                              {String(rawExif[key])}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExifMetadataDrawer;
