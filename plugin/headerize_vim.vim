" VIM SCRIPT: ~/.vim/bundle/headerize-vim/plugin/headerize_vim.vim
" Description: Inserts copyright header on new file creation.

" Only apply for new, unsaved files (or files with 0 lines)
autocmd BufNewFile * call HeaderizeInsert()

function! HeaderizeInsert()
    " Check if the buffer is empty (new file)
    " We check for empty content or a single, blank line.
    if line('$') > 1 || getline(1) != ''
        return
    endif

    " Get the current file name/extension
    let l:filename = expand('%:t')
    if empty(l:filename)
        return
    endif

    " 1. Define the command path. Assumes successful installation to ~/.local/bin
    let l:command_path = expand('~/.local/bin/headerize.py')

    " 2. Construct the command to call headerize with the -ft flag
    let l:command = l:command_path . ' -ft ' . shellescape(l:filename)

    " 3. Execute the command and capture the output
    " We use 'silent' to avoid showing the 'system()' command output in the status bar
    let l:header = system(l:command)

    " 4. Insert the output into the current buffer
    if !empty(l:header)
        " Insert the header content at line 1
        " split() handles multi-line output correctly
        call setline(1, split(l:header, '\n'))
        " Move cursor to the end of the inserted text
        normal! Go
    endif
endfunction
