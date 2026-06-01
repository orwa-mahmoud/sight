import { Alert, Button, Stack } from "@mantine/core";
import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  readonly children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      console.error("ErrorBoundary caught:", error, info);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <Stack align="center" justify="center" py="xl">
          <Alert color="red" title="Something went wrong" maw={480}>
            An unexpected error occurred. Please try again.
          </Alert>
          <Button variant="light" onClick={() => this.setState({ hasError: false })}>
            Retry
          </Button>
        </Stack>
      );
    }
    return this.props.children;
  }
}
