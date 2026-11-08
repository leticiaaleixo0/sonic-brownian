// Error Message component: displays an error message if something goes wrong
export function ErrorMessage({ message }){
    if (!message) return null;
    return (
        <div className="error-message">
            <p>Erro: {message}</p>
        </div>
    )
}
