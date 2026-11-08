import { DemoSection } from "../sections/DemoSection.jsx";
import { PaperHeader } from "../sections/PaperHeader.jsx";
import { TheorySection } from "../sections/TheorySection.jsx";


// Home Page: header, the demo with the hyperparameter panel, then the theory behind the model
export function HomePage() {
    return (
        <div className="paper-container">
            <PaperHeader />
            <DemoSection />
            <hr className="section-divider" />
            <TheorySection />
        </div>
    );
}
