use minisign_verify::{PublicKey, Signature};
use std::{env, fs::File, io::Read, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        return Err("usage: oxo-verify-updater <public-key> <signature> <installer>".into());
    }

    let public_key = PublicKey::from_file(Path::new(&args[1]))?;
    let signature = Signature::from_file(Path::new(&args[2]))?;
    let mut verifier = public_key.verify_stream(&signature)?;
    let mut installer = File::open(&args[3])?;
    let mut buffer = vec![0_u8; 1024 * 1024];
    loop {
        let read = installer.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        verifier.update(&buffer[..read]);
    }
    verifier.finalize()?;
    println!("updater signature verified");
    Ok(())
}
