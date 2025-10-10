#!/usr/bin/env python3
"""
Interactive Dialogue Creator
Creates alternating dialogue between two speakers with customizable emojis.
"""

import pyperclip

def main():
    # Customizable speaker emojis/names
    SPEAKER_A = "🐉"  # Change this emoji/symbol for speaker A
    SPEAKER_B = "😈"  # Change this emoji/symbol for speaker B
    
    print("=== Interactive Dialogue Creator ===")
    print("Type your dialogue lines. Press Enter on empty line to finish.")
    print("Type 'quit' to exit anytime.\n")
    
    dialogue = []
    current_speaker = SPEAKER_A
    speakers = {SPEAKER_A: "A", SPEAKER_B: "B"}
    
    while True:
        # Prompt for input
        speaker_label = speakers[current_speaker]
        prompt = f"{current_speaker} ({speaker_label}): "
        
        try:
            user_input = input(prompt).strip()
            
            # Check for exit conditions
            if user_input.lower() == 'quit':
                break
            
            # Empty line finishes dialogue
            if not user_input:
                break
            
            # Add to dialogue with guaranteed double space at end
            dialogue.append(f"{current_speaker}: {user_input}  ")
            
            # Switch speakers
            current_speaker = SPEAKER_B if current_speaker == SPEAKER_A else SPEAKER_A
            
        except KeyboardInterrupt:
            print("\n\nDialogue creation interrupted.")
            break
    
    # Display final dialogue
    if dialogue:
        print("\n" + "="*40)
        print("FINAL DIALOGUE:")
        print("="*40)
        
        # Create dialogue text for display and clipboard
        dialogue_text = "\n".join(dialogue)
        
        for line in dialogue:
            print(line)
        
        # Copy to clipboard
        try:
            pyperclip.copy(dialogue_text)
            print("\n✅ Dialogue copied to clipboard!")
        except Exception as e:
            print(f"\n❌ Could not copy to clipboard: {e}")
        
        # Option to save to file
        save_choice = input("\nSave dialogue to file? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes']:
            save_dialogue(dialogue)
    else:
        print("\nNo dialogue created.")

def save_dialogue(dialogue):
    """Save dialogue to a text file."""
    try:
        filename = input("Enter filename (without extension): ").strip()
        if not filename:
            filename = "dialogue"
        
        filename = f"{filename}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("DIALOGUE\n")
            f.write("="*40 + "\n")
            for line in dialogue:
                f.write(line + "\n")
        
        print(f"Dialogue saved to `{filename}`")
        
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()