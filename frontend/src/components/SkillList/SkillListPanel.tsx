import { useEffect } from "react";
import { useSkillStore } from "@/stores/skillStore";
import { SkillCard } from "./SkillCard";
import { SkillDetail } from "./SkillDetail";

export function SkillListPanel() {
  const { skills, selectedSkill, loadSkills, selectSkill, clearSelection, toggleEnabled, removeSkill } =
    useSkillStore();

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  if (selectedSkill) {
    return (
      <SkillDetail
        skill={selectedSkill}
        onClose={clearSelection}
        onDelete={() => removeSkill(selectedSkill.name)}
      />
    );
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-xl font-bold">Skills</h1>
      {skills.length === 0 ? (
        <p className="text-sm text-muted-foreground">No skills installed yet.</p>
      ) : (
        <div className="space-y-3">
          {skills.map((skill) => (
            <SkillCard
              key={skill.name}
              skill={skill}
              onClick={() => selectSkill(skill.name)}
              onToggle={(enabled) => toggleEnabled(skill.name, enabled)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
