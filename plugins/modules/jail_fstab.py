#!/usr/bin/python
__metaclass__ = type

# XXX - One-line description of module
# Manage a jail's fstab

# XXX
DOCUMENTATION = '''
---
module: jail_fstab
short_description: "Manage a jail's fstab"
description:
  - Add, remove, mount, and unmount filesystems that a jail sees.
options:
  append:
    description:
      - If C(yes), other filesystems may be mounted besides the ones listed
        in C(fstab).
      - If C(no), any mounts other than the ones in C(fstab) will be removed.
    type: bool
    default: no
  jail:
    description:
      - Name of the jail
    type: str
    required: yes
  fstab:
    description:
      - List of mount points. Each element is a dictionary.
    type: list
    suboptions:
      src:
        description:
          - The device to mount, or the directory to share with the jail.
        required: yes
        type: str
      mount:
        description:
          - The directory where the device should be mounted.
          - If this begins with C(/), it is an absolute path, as seen
            from outside the jail. Otherwise, it is a relative path,
            relative to the jail's root, typically
            C(/mnt/<pool>/iocage/jails/<jail-name>/root).
        required: yes
        type: str
      fstype:
        description:
          - Filesystem type.
          - When mounting an existing directory, use C(nullfs).
        type: str
        required: no
        default: "nullfs"
      options:
        description:
          - Filesystem options to pass to C(mount). Comma-separated string.
        type: str
        default: "ro"
      dump:
        description:
          - Used by the C(dump) command. This field gives the number of
            days between backups. A value of 0 means "no backups".
          - This is the C(fs_freq) field in fstab(5).
          - For a jail, this will typically be 0.
        type: int
        required: no
        default: 0
      fsck_pass:
        description:
          - Used by C(fsck) to determine the order in which to check
            filesystems at boot time.
          - This is not normally useful in a jail. It is included here
            for completeness.
        type: int
        required: no
        default: 0
version_added: XXX
'''

EXAMPLES = '''
- name: Mount some directories inside a jail
  arensb.truenas.jail_fstab:
    jail: the-jail-name
    fstab:
      # Absolute mount point:
      - src: /mnt/data/my-data
        mount: /mnt/data/iocage/jails/the-jail-name/root/my-data
        fstype: nullfs
        options: ro
        dump: 0
        pass: 0
      # Relative mount point:
      - src: /mnt/data/more-data
        mount: data/more
'''

# XXX
RETURN = '''
fstab:
  description:
    - The jail's fstab.
    - This is returned in check mode as well.
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.arensb.truenas.plugins.module_utils.middleware \
    import MiddleWare as MW

iocroot = None

def main():
    def get_iocroot():
        global iocroot

        # Return cached value, if there is one.
        if iocroot is not None:
            return iocroot

        # Look up the iocage root.
        try:
            iocroot = mw.call("jail.get_iocroot", output='str')
        except Exception as e:
            return None

        return iocroot

    module = AnsibleModule(
        argument_spec=dict(
            jail=dict(type='str', required=True),
            fstab=dict(type='list', elements='dict',
                       options=dict(
                           src=dict(type='str', required=True),
                           mount=dict(type='str', required=True),
                           fstype=dict(type='str', default="nullfs"),
                           options=dict(type='str', default="ro"),
                           dump=dict(type='int', default=0),
                           fsck_pass=dict(type='int', default=0),
                       )),
            append=dict(type='bool', default=False),
            ),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        msg=''
    )

    mw = MW.client()

    # Assign variables from properties, for convenience
    jail = module.params['jail']
    fstab = module.params['fstab']
    append = module.params['append']

    result['iocroot'] = get_iocroot()

    # Look up the jail and its fstab
    try:
        fstab_info = mw.call("jail.fstab",
                             jail,
                             {"action": "LIST"})

    except Exception as e:
        module.fail_json(msg=f"Error looking up jail {jail}: {e}")

    # Filter out the "SYSTEM" entries and only keep the "USER" ones.
    fstab_info = {k: v for (k, v) in fstab_info.items()
                  if v['type'] == "USER"}
    result['fstab'] = fstab_info

    # Iterate over the provided list of mount points and see if they
    # match what the caller wants.

    # XXX - Need to stop jail when adding, removing a mountpoint.

    # Make a list of changes to apply. This is a list of elements of
    # the form
    # { action: <action>, entry: <entry> }
    # where <action> is one of "add", "remove", or "replace"
    # and <entry> is an element from the `fstab' parameter.
    changes = []

    for fs in fstab:
        # XXX - Debugging
        result['msg'] += f"Checking {fs['mount']}.\n"

        mount_full = fs['mount']
        if not mount_full.startswith("/"):
            # This is a relative path. Make it absolute.
            mount_full = f"{get_iocroot()}/jails/{jail}/root/{fs['mount']}"

        result['msg'] += f"  mount_full: {mount_full}\n"
        # Look for this fstab entry. This construct is "clever", so
        # may need to be rewritten:
        # - Iterate over all k=>v items in fstab_info.
        #   k is an integer, the item's position in fstab, and
        #   isn't interesting.
        #   v is {"entry: [src, mount, fstab, options, dump, fsck_pass]}
        # - We grep out the ones where 'mount' is the one we want.
        # - Use next() to pick only the first item, if one exists, or
        #   return None as a default, if no suitable entry is found.
        entry = next((v['entry'] for (k, v) in fstab_info.items()
                      if v['entry'][1] == mount_full),
                     None)

        if entry is None:
            # XXX - This entry does not exist in the jail. Need to
            # create it.
            result['msg'] += f"No such entry. Need to add it.\n"

            # XXX - Required fields for ADD:
            # - source
            # - destination
            # others are optional.

            # XXX - Required fields for REMOVE:
            # - source
            # - destination
        else:
            # XXX - This entry exists in the jail. Make sure it's
            # okay.
            result['msg'] += f"This entry exists. Need to check it.\n"

        # XXX - If "mount" begins with "/", it's absolute. Otherwise,
        # it's relative to jail root:
        # {iocroot}/jails/{jailname}/root

        # XXX - Figure out whether to ADD or REPLACE this fstb entry,
        # or leave it alone.

    if append:
        result['msg'] += "Other fs-es may exist.\n"
    else:
        result['msg'] += "Ought to delete other fs-es.\n"

        # XXX - For any remaining fstab entries:
        # jail.fstab <jail-name> {entry, action: REMOVE}

    module.exit_json(**result)

    # XXX - Everything below is left over from the template. Delete it.

    # First, check whether the resource even exists.
    if fstab_info is None:
        # Resource doesn't exist

        if state == 'present':
            # Resource is supposed to exist, so create it.

            # Collect arguments to pass to resource.create()
            arg = {
                "resourcename": jail,
            }

            if feature is not None:
                arg['feature'] = feature

            if module.check_mode:
                result['msg'] = f"Would have created resource {jail} with {arg}"
            else:
                #
                # Create new resource
                #
                try:
                    err = mw.call("resource.create", arg)
                    result['msg'] = err
                except Exception as e:
                    result['failed_invocation'] = arg
                    module.fail_json(msg=f"Error creating resource {jail}: {e}")

                # Return whichever interesting bits resource.create()
                # returned.
                result['resource_id'] = err

            result['changed'] = True
        else:
            # Resource is not supposed to exist.
            # All is well
            result['changed'] = False

    else:
        # Resource exists
        if state == 'present':
            # Resource is supposed to exist

            # Make list of differences between what is and what should
            # be.
            arg = {}

            if feature is not None and fstab_info['feature'] != feature:
                arg['feature'] = feature

            # If there are any changes, resource.update()
            if len(arg) == 0:
                # No changes
                result['changed'] = False
            else:
                #
                # Update resource.
                #
                if module.check_mode:
                    result['msg'] = f"Would have updated resource {jail}: {arg}"
                else:
                    try:
                        err = mw.call("resource.update",
                                      fstab_info['id'],
                                      arg)
                    except Exception as e:
                        module.fail_json(msg=f"Error updating resource {jail} with {arg}: {e}")
                        # Return any interesting bits from err
                        result['status'] = err['status']
                result['changed'] = True
        else:
            # Resource is not supposed to exist

            if module.check_mode:
                result['msg'] = f"Would have deleted resource {jail}"
            else:
                try:
                    #
                    # Delete resource.
                    #
                    err = mw.call("resource.delete",
                                  fstab_info['id'])
                except Exception as e:
                    module.fail_json(msg=f"Error deleting resource {jail}: {e}")
            result['changed'] = True

    module.exit_json(**result)


# Main
if __name__ == "__main__":
    main()
