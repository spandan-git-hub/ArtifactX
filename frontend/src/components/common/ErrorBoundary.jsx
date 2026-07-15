import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const { fallback, showDetails = false } = this.props;

      if (fallback) {
        return fallback(this.state.error, this.handleRetry);
      }

      return (
        <div className="p-6 max-w-md mx-auto">
          <div className="card border-accent-rose/30 text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent-rose/10 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="h-8 w-8 text-accent-rose" />
            </div>
            <h2 className="text-lg font-semibold text-forensic-100 mb-2">
              Something went wrong
            </h2>
            <p className="text-sm text-forensic-500 mb-4">
              We encountered an unexpected error. Please try again.
            </p>
            {showDetails && this.state.error && (
              <div className="text-left bg-forensic-900 rounded-lg p-3 mb-4 overflow-auto">
                <pre className="text-xs text-accent-rose whitespace-pre-wrap">
                  {this.state.error.message || String(this.state.error)}
                </pre>
              </div>
            )}
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={this.handleRetry}
                className="btn-secondary inline-flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="btn-ghost inline-flex items-center gap-2"
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;