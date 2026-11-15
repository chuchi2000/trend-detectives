import { AtlasStateProvider } from "@/context/AtlasStateContext";
import { LanguageProvider } from "@/i18n/LanguageProvider";
import { useRoute } from "@/hooks/useRoute";
import { AtlasPage } from "@/pages/AtlasPage";
import { WelcomePage } from "@/pages/WelcomePage";

/**
 * Raíz de la aplicación: bienvenida ("/") o área de exploración ("/atlas").
 * El estado del Atlas se crea al entrar a /atlas y se lee de la URL, así que
 * el modo elegido en la bienvenida llega como ?modo=...
 */
export default function App() {
  const [route, navigate] = useRoute();
  return (
    <LanguageProvider>
      {route === "inicio" ? (
        <WelcomePage onEnter={(mode) => navigate("atlas", `?modo=${mode}`)} />
      ) : (
        <AtlasStateProvider>
          <AtlasPage onHome={() => navigate("inicio")} />
        </AtlasStateProvider>
      )}
    </LanguageProvider>
  );
}
