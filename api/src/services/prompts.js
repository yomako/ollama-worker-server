import fs from "fs";

export function loadPrompt(name, input) {
  const tpl = fs.readFileSync(`../shared/prompts/${name}.txt`, "utf-8");
  return tpl.replace("{{INPUT}}", input);
}
