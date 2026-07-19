import type { ErrorInfo, PropsWithChildren, ReactNode } from "react";
import { Component } from "react";

type Props = PropsWithChildren<{ fallback?: ReactNode }>;
type State = { hasError: boolean };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    void error;
    void errorInfo;
    // Hook for production logging.
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-rose-700">
            Something went wrong while rendering this module.
          </div>
        )
      );
    }
    return this.props.children;
  }
}
