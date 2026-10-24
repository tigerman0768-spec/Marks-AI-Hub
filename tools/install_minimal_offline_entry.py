from pathlib import Path
root = Path(__file__).resolve().parents[1] / "app"
main = root / "lib/main.dart"
if not (root / "lib/film_creator_screen.dart").exists():
    raise SystemExit("Film Creator screen missing")
main.write_text(r"""import 'package:flutter/material.dart';
import 'film_creator_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MarksAiOfflineApp());
}

class MarksAiOfflineApp extends StatelessWidget {
  const MarksAiOfflineApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Mark's AI Film Creator",
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF20B8A5), brightness: Brightness.dark),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF10151D),
      ),
      home: const FilmCreatorScreen(),
    );
  }
}
""", encoding="utf-8")
print("Installed minimal offline Film Creator entry point.")
