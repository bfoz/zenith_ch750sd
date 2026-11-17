on run {input_file, output_path}
    -- This must stay inside the run handler: AppleScript rejects a script that has top-level statements *and* an `on run` handler (error -2752)
    -- Wrapped list items need the explicit line-continuation character (option-L in Script Editor); a bare newline inside the braces fails with -2741
    -- A trailing comma before the closing brace is likewise a syntax error, though a trailing continuation mark is accepted.
    -- Parts to export. This is the complete set of meshes in stl/, so that running
    -- this script reproduces the STL files ch750sd.py expects. Keep it in step with
    -- stl/: a mesh missing from this list is silently missing from the reference
    -- assembly, and ch750sd.py just globs whatever is on disk.
    -- Names must match the eDrawings window titles, which are the part names; they
    -- are what the generated STL files are named after.
    -- A -- comment inside the list braces is a syntax error (-2741), so to exclude a
    -- part temporarily, cut the line out rather than commenting it in place.
    -- Deliberately absent: the two C75C3-6 lateral pedal bearing blocks. The
    -- rudder pedal brackets in RudderPedalBracketAssembly.FCStd replace them, so
    -- the reference assembly shows the as-built parts at that station instead of
    -- the kit parts they supersede. They are still in the airframe document, so
    -- to bring them back cut the two lines back in:
    --     "C75C3-6 LATERAL PEDAL BEARING LEFT-2"
    --     "C75C3-6 LATERAL PEDAL BEARING-3"
    set part_list to {¬
        "75F16-2 FORWARD TOP SKIN-3", ¬
        "C75C3-3 RUDDER PEDALS - LEFT-1", ¬
        "C75C3-3 RUDDER PEDALS - RIGHT-1", ¬
        "C75C4-3   RUDDER CABLE FAIR LEAD-1", ¬
        "C75C4-3   RUDDER CABLE FAIR LEAD-2", ¬
        "C75F8-3   FIREWALL SIDE STIFFENER-1", ¬
        "C75F8-4   FIREWALL TOP STIFFENER-1", ¬
        "C75F8-6   SIDE BRACE-4", ¬
        "C75F8-8   SLIDE COVER-1", ¬
        "C75F8-8   SLIDE COVER-2", ¬
        "C75F9-1   FORWARD GUSSET-1", ¬
        "C75F9-2   UPPER ANGLE-1", ¬
        "C75F9-7   UPPER FIREWALL CHANNEL-1", ¬
        "LS75C34-5   ELEVATOR CABLE BEARING - JUMPSEAT-1", ¬
        "LS75C34-5   ELEVATOR CABLE BEARING - JUMPSEAT-2", ¬
        "LS75F1-1 BOTTOM FUSELAGE SKIN-1", ¬
        "LS75F33-1   JUMPSEAT REAR CHANNEL-1", ¬
        "LS75F8-9   L ANGLE - FIREWAL AND TOP STIFFENER -1", ¬
        "LS75F9-4  CENTER FREWALL STIFFENER-3", ¬
        "MirrorC75F2-2 BOTTM EXT.-3", ¬
        "MirrorC75F8-3   FIREWALL SIDE STIFFENER-2", ¬
        "MirrorC75F8-6   SIDE BRACE-7", ¬
        "MirrorLS75F18-1   VERTICAL L ANGLE-4", ¬
        "MirrorLS75F18-2   DIAGONAL L ANGLE-2", ¬
        "MirrorSD75F40-1 FORWARD SIDE SKIN-2", ¬
        "MirrorSD75F40-13   GEAR GUSSET-2", ¬
        "SD75F19-1   LONGITUDINAL Z ANGLE -3", ¬
        "SD75F19-2   LATERAL  Z ANGLE -1", ¬
        "SD75F40-1 FORWARD SIDE SKIN-1", ¬
        "SD75F40-13   GEAR GUSSET-1", ¬
        "SD75F40-4 FIREWALL - SQUARE BOTTOM-2"¬
    }

    if output_path is missing value then
        set output_path to "stl"
    end if

    -- Find the filename of the path for the input file
    set oldDelims to AppleScript's text item delimiters
    set AppleScript's text item delimiters to "/"
    set input_filename to last text item of input_file
    set AppleScript's text item delimiters to oldDelims

    repeat with part_name in part_list

        if application "eDrawings" is running
            set quit_on_exit to false
        else
            tell application "eDrawings" to activate
            tell application "System Events"
                repeat until exists application process "eDrawings"
                    delay 0.1
                end repeat
            end tell
            set quit_on_exit to true
        end if

        tell application "System Events"
            tell process "eDrawings"
                -- Bring the application window to the absolute front
                set frontmost to true

                -- Wait up to 3 seconds for the app to initialize and show a window
                repeat 30 times
                    if exists window 1 then exit repeat
                    delay 0.1
                end repeat

                -- See if a window for the part already exists
                if not exists (first window whose title contains part_name)
                    if exists (first window whose title contains input_filename)
                        set input_window to first window whose title contains input_filename
                    else if exists (window 1 whose title contains "Open") then
                        -- Detect if the first window is an "Open" dialog
                        my handle_open_dialog(input_file)
                        set input_window to my wait_for_window(input_filename)
                    else if not exists (window 1 whose title contains "Open") then
                        -- If no Open dialog appeared, use the standard menu bar to open the file
                        keystroke "o" using {command down}
                        delay 0.1

                        my handle_open_dialog(input_file)
                        set input_window to my wait_for_window(input_filename)
                    else
                        log "Failed to open" & input_filename
                    end if

                    tell input_window
                        -- Select and focus the text box
                        set search_field to text field 1 of group 1 of splitter group 1
                        set focused of search_field to true
                        set value of search_field to ""
                        keystroke part_name

                        set scroll_area to scroll area 1 of group 1 of splitter group 1
                        set outliner to outline 1 of scroll_area
                        set visible_rows to rows of outliner
                        set last_row to last item of visible_rows
                        set selected_text_field to text field 1 of last_row

                        delay 0.1

                        tell selected_text_field
                            select
                            perform action "AXShowMenu"
                        end tell

                        delay 0.1

                        click menu item "New Part Document" of menu 1 of outliner
                    end tell
                end if

                -- Find the window that opened
                set part_window to my wait_for_window(part_name)

                -- Make the output directory before trying to save the file
                tell application "Finder"
                    -- Check if the specific folder name does not exist in the parent folder
                    if not (exists folder output_path) then
                        set scriptDirectory to container of (path to me) as text
                        try
                            make new folder at folder scriptDirectory with properties {name:output_path}
                        end try
                    end if
                end tell

                tell part_window
                    -- Tell the window to close because that will bring up the Save dialog
                    click (first button whose subrole is "AXCloseButton")
                    delay 0.3

                    -- Choose to Save the file
                    set alert_sheet to sheet 1
                    set save_button to first button of alert_sheet whose name is "Save"
                    click save_button

                    -- eDrawings throws a weird alert that can only be dismissed
                    repeat until exists sheet 1
                        delay 0.2
                    end repeat
                    set alert_sheet to sheet 1
                    set ok_button to first button of alert_sheet whose name is "OK"
                    tell part_window to click ok_button

                    -- Wait until the Save sheet or window is active
                    repeat until exists sheet 1
                        delay 0.2
                    end repeat

                    -- Change the path to the output path
                    keystroke "g" using {command down, shift down}
                    delay 0.3

                    keystroke output_path
                    keystroke return
                    delay 0.3

                    set save_sheet to sheet 1

                    -- Change the format to STL
                    set format_button to first pop up button of splitter group 1 of save_sheet whose value contains "eDrawings"
                    click format_button
                    delay 0.2
                    tell format_button
                        click menu item "STL" of menu 1
                    end tell

                    delay 0.3

                    -- Click Save
                    set save_button to first button of splitter group 1 of save_sheet whose title is "Save"
                    click save_button

                    delay 0.5

                    if exists sheet 1 of save_sheet then
                        tell sheet 1 of save_sheet
                            if exists button "Replace" then
                                click button "Replace"
                            end if
                        end tell
                    end if
                end tell

                if quit_on_exit then quit
            end tell
        end tell
    end repeat
end run

on handle_open_dialog(input_file)
    tell application "System Events"
        -- Bring up the "Go to Folder" drawer inside the Open dialog
        keystroke "g" using {command down, shift down}
        delay 0.4

        -- Input the full file path and press Return to confirm the path
        keystroke input_file
        delay 0.2
        keystroke return
        delay 0.4

        -- Press Return one more time to trigger the final "Open" button
        keystroke return
    end tell
end handle_open_dialog

on wait_for_window(window_title)
    tell application "System Events"
        tell process "eDrawings"
            repeat 30 times
                if exists (first window whose title contains window_title) then return (first window whose title contains window_title)
                delay 0.1
            end repeat
        end tell
    end tell
end wait_for_window
