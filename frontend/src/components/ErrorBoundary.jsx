import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="error-screen">
          <section className="surface error-panel">
            <h1>Erreur d'affichage</h1>
            <p>Une erreur a empeche le chargement de l'interface.</p>
            <button
              className="primary-button"
              onClick={() => {
                localStorage.removeItem("uor_token");
                localStorage.removeItem("uor_user");
                window.location.assign("/login");
              }}
            >
              Reinitialiser la session
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
