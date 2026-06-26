import { Image, Video, Music, FileText, FolderOpen } from 'lucide-react';

const MediaList = ({ evidenceId, media }) => {
  const getMediaIcon = (mediaType) => {
    switch (mediaType) {
      case 'image':
        return <Image className="h-6 w-6 text-accent-emerald" />;
      case 'video':
        return <Video className="h-6 w-6 text-accent-violet" />;
      case 'audio':
        return <Music className="h-6 w-6 text-accent-amber" />;
      default:
        return <FileText className="h-6 w-6 text-forensic-500" />;
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Image className="h-5 w-5 text-accent-violet" />
        <span className="font-semibold text-forensic-100">Media References</span>
        <span className="badge badge-violet">{media.length}</span>
      </div>

      {media.length === 0 ? (
        <div className="text-center py-8">
          <FolderOpen className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No WhatsApp media references found.</p>
          <p className="text-sm text-forensic-600 mt-1">Analyze evidence to extract media.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Message ID</th>
                <th>Path</th>
                <th>Size</th>
                <th>Dimensions</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {media.map((m, idx) => (
                <tr key={m.message_id || m.id || idx}>
                  <td>
                    <div className="flex items-center gap-2">
                      {getMediaIcon(m.media_type)}
                      <span className="capitalize text-forensic-300">
                        {m.media_type || 'unknown'}
                      </span>
                    </div>
                  </td>
                  <td className="text-forensic-400 font-mono text-sm">
                    {m.message_id || 'N/A'}
                  </td>
                  <td className="text-forensic-400 text-sm truncate max-w-[200px]">
                    {m.media_path || 'Unknown'}
                  </td>
                  <td className="text-forensic-400 font-mono text-sm">
                    {formatFileSize(m.file_size)}
                  </td>
                  <td className="text-forensic-400">
                    {m.width && m.height ? (
                      <span className="font-mono text-sm">{m.width} × {m.height}</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="text-forensic-400">
                    {m.duration ? (
                      <span className="font-mono text-sm">{m.duration.toFixed(2)}s</span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default MediaList;